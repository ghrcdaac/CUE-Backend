import os
import json
import time
import structlog
from typing import Any, Dict, Set, Tuple, List
from uuid import UUID
import asyncpg
import boto3
from model import RedrivePayload
from db import validate_unscanned_file
from botocore.exceptions import ClientError
from pydantic import ValidationError

logger = structlog.get_logger()

sqs = boto3.client("sqs")

class ManualInfectedLoggerError(Exception):
    pass

DLQ_URL = os.environ.get("DLQ_URL", "") 
SOURCE_QUEUE_URL = os.environ.get("SOURCE_QUEUE_URL", "")
try:
    MAX_BATCH = int(os.environ.get("MAX_BATCH", 10))
    WAIT_SECONDS = int(os.environ.get("WAIT_SECONDS",10))
    MAX_SECONDS = int(os.environ.get("MAX_SECONDS", 120)) # 1 minute before lambda timeout
    MAX_EMPTY_POLLS = int(os.environ.get("MAX_EMPTY_POLLS", 6))
except ValueError as e:
    logger.info("failed_to_initialize_environment_variables")
    raise ManualInfectedLoggerError(str(e))


async def validate_files(pool: asyncpg.Pool, redrive_payload: dict) -> Tuple[List[UUID], List[str]]:
    try:
        parsed_redirive_payload = RedrivePayload(**redrive_payload)
    except ValidationError as e:
        logger.error("redrive_payload.invalid", exc_info=True)
        raise ManualInfectedLoggerError(str(e))

    validated_ids = [] 
    invalid_ids = []

    async with pool.acquire() as conn: 
        for file_id in parsed_redirive_payload.file_ids:
            # check if file exists and file status is unscanned 
            if await validate_unscanned_file(conn, file_id):
                validated_ids.append(file_id)
            else: 
                invalid_ids.append(str(file_id))

    return (validated_ids, invalid_ids)

async def poll_and_redrive(file_ids) -> Dict[str, Any]:
    """Polls cue_scan_results_dlq for message containing results associated with file_ids.
       Redrives message from dlq to cue_scan_results_queue. Gracefully exits before lambda function timeout. """

    start = time.time()
    moved_total = 0
    examined_total = 0
    errors_total = 0
    empty_polls = 0
    moved_ids: Set[UUID] = set()
    set_file_ids: Set[UUID] = set(file_ids)

    while True:
        if time.time() - start > MAX_SECONDS:
            logger.info("break_loop.timeout_safety_cap")
            break

        try:
            resp = sqs.receive_message(
                QueueUrl=DLQ_URL,
                MaxNumberOfMessages=MAX_BATCH,
                WaitTimeSeconds=WAIT_SECONDS,
                AttributeNames=["All"],
                MessageAttributeNames=["All"]
            )
            messages = resp.get("Messages", []) or []
        except ClientError as e:
            # Treat receive failure as unrecoverable for this run
            logger.error(f"receive_message_from_dlq.failed", exc_info=True)
            not_redriven = sorted([str(file_id) for file_id in list(set_file_ids - moved_ids)])
            return {
                "moved_total": moved_total,
                "examined_total": examined_total,
                "errors_total": errors_total,
                "not_redriven": not_redriven 
            }

        if not messages:
            empty_polls += 1
            if empty_polls >= MAX_EMPTY_POLLS:
                logger.info("break_loop.consecutive_empty_polls")
                break
            continue
        else:
            empty_polls = 0

        for msg in messages:
            examined_total += 1
            body_text = msg.get("Body", "")
            msg_attrs = msg.get("MessageAttributes", {}) or {}

            # Parse JSON body and match id
            try:
                body = json.loads(body_text)
            except json.JSONDecodeError: 
                # Could not parse body into JSON leave message on dlq and move on to next message
                continue

            # Get file_id(key) from body
            file_id = body.get('key')
            try:
                #extract file_id as uuid if file_id exists and is valid
                file_id_uuid = UUID(file_id) if file_id is not None else None
            except Exception as e:
                # Could not extract file_id as uuid leave message on dlq and move on to next message
                continue

            if file_id_uuid is None or file_id_uuid not in file_ids:
                # file_id_uuid is None or is not in file_ids list leave message on dlq and move on to next message
                continue

            # Forward and delete
            try:
                logger.info("forwarding_message_from_dlq_to_source_queue", file_id=file_id_uuid, message_body=body)
                sqs.send_message(
                    QueueUrl=SOURCE_QUEUE_URL,
                    MessageBody=body_text,
                    MessageAttributes=msg_attrs
                )
                sqs.delete_message(QueueUrl=DLQ_URL, ReceiptHandle=msg["ReceiptHandle"])
                moved_total += 1
                moved_ids.add(file_id_uuid)
            except Exception as e:
                errors_total += 1
                logger.exception("forwarding_message.failed", file_id={file_id_uuid}, message_body=body, error=e)

            # Take the difference between the set of file_ids given and the set of moved_file_ids.
            # If empty set remains break out of loop
        if not (set_file_ids - moved_ids):
            logger.info("break_loop.all_messages_found")
            break

    not_redriven = sorted([str(file_id) for file_id in list(set_file_ids - moved_ids)])
    logger.info("results", moved_total=moved_total, examined_total=examined_total, errors_total=errors_total)  
    return { 
        "moved_total": moved_total,
        "errors_total": errors_total,
        "not_redriven": not_redriven 
    }
