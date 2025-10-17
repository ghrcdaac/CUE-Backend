import boto3
from botocore.exceptions import ClientError
from uuid import UUID
import json
import os
from typing import Dict, List, Any, Optional, Tuple
import structlog
import asyncpg
import hashlib
import base64
import asyncio

from db import (
    safely_advance_file_status_batch,
    update_status_with_checksum_failure
)

logger = structlog.get_logger(__name__)
s3_client = boto3.client('s3')

STAGING_BUCKET = os.environ.get("STAGING_BUCKET", "")
VERIFY_CHECKSUM = os.environ.get("VERIFY_CHECKSUM_ON_TRANSFER", "true").lower() == "true"


async def parse_sqs_message(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parses the body of an SQS record into a dictionary."""
    try:
        message_body_str = message.get('body')
        if not message_body_str:
            logger.error("sqs.record.body.missing", record_id=message.get("messageId"))
            return None
        return json.loads(message_body_str)
    except json.JSONDecodeError:
        logger.warning("sqs.record.body.invalid_json", body=message_body_str, record_id=message.get("messageId"))
        return None

async def process_messages(records: List[Dict]) -> Tuple[Dict[str, Dict], List[UUID]]:
    """Parses SQS records, validates them, and extracts file IDs for batch processing."""
    messages = {}
    file_ids = []
    logger.info("sqs.batch.processing_messages", record_count=len(records))
    for record in records:
        message_id = record["messageId"]
        message_body = await parse_sqs_message(record)
        
        if not message_body or not message_body.get("file_id") or not message_body.get("collection_id"):
            logger.warning("process_message.skip.invalid_or_incomplete_body", message_id=message_id, body=message_body)
            continue
        
        try:
            messages[message_id] = message_body
            file_ids.append(UUID(message_body["file_id"]))
        except (ValueError, TypeError) as e:
            logger.error("process_message.skip.invalid_uuid", message_id=message_id, body=message_body, error=str(e))
            continue
            
    logger.info("sqs.batch.messages_processed", valid_message_count=len(messages))
    return messages, file_ids

async def verify_staging_object_sha256(file_id: str) -> str:
    """Downloads an S3 object from the staging bucket and computes its SHA256 hash."""
    sha256_hash = hashlib.sha256()
    
    def download_and_hash():
        try:
            response = s3_client.get_object(Bucket=STAGING_BUCKET, Key=file_id)
            body = response['Body']
            for chunk in body.iter_chunks(chunk_size=8192 * 1024): # 8MB chunks
                sha256_hash.update(chunk)
        except ClientError as e:
            logger.error("s3.get_object.failed_from_staging", key=file_id, error_code=e.response['Error']['Code'])
            raise
            
    await asyncio.to_thread(download_and_hash)
    return base64.b64encode(sha256_hash.digest()).decode('utf-8')

async def copy_file_to_dest(src_key: str, dest_bucket: str, dest_key: str):
    """Copies a file to its destination, with an internal retry mechanism for transient errors."""
    copy_source = {"Bucket": STAGING_BUCKET, "Key": src_key}
    max_retries = 3
    retry_delay_base = 2

    for attempt in range(max_retries):
        try:
            # Run the synchronous boto3 call in a separate thread
            await asyncio.to_thread(
                s3_client.copy_object,
                CopySource=copy_source,
                Bucket=dest_bucket,
                Key=dest_key,
                ACL="bucket-owner-full-control"
            )
            # This log is crucial for auditing successful transfers.
            logger.info("s3.copy.success", file_id=src_key, dest_bucket=dest_bucket, dest_key=dest_key)
            return
        except ClientError as e:
            # Retry only on specific, transient S3 errors
            if e.response['Error']['Code'] in ['ServiceUnavailable', 'SlowDown', 'InternalError'] and attempt < max_retries - 1:
                delay = retry_delay_base * (2 ** attempt)
                logger.warning("s3.copy.transient_error.retrying", attempt=attempt + 1, file_id=src_key, delay=delay, error_code=e.response['Error']['Code'])
                await asyncio.sleep(delay)
            else:
                logger.error("s3.copy.failed.persistent_error", src_key=src_key, dest_key=dest_key, error_code=e.response['Error']['Code'])
                raise

async def batch_transfer_and_validate(
    messages: Dict[str, Dict],
    transfer_details: Dict[UUID, Dict]
) -> Tuple[List[UUID], List[Dict[str, Any]], List[Dict[str, str]]]:
    """Orchestrates the transfer and validation for a batch of files."""
    hard_failures = []
    successful_file_ids = []
    validation_failures = []

    for message_id, msg_body in messages.items():
        file_id = UUID(msg_body['file_id'])
        details = transfer_details.get(file_id)

        if not details:
            logger.warning("batch_transfer.skip.no_metadata_or_not_ready", file_id=str(file_id), message_id=message_id)
            continue

        file_info = details["file_info"]
        egress = details["egress"]
        dest_bucket = egress.get("config", {}).get("bucket")

        if not dest_bucket:
            logger.error("batch_transfer.failed.no_destination_bucket", file_id=str(file_id), message_id=message_id)
            hard_failures.append({"itemIdentifier": message_id})
            continue

        path_parts = [p for p in [egress.get("config", {}).get("destination_path"), file_info.get("collection_path"), file_info["name"]] if p]
        dest_key = os.path.join(*path_parts)

        try:
            await copy_file_to_dest(str(file_id), dest_bucket, dest_key)

            if VERIFY_CHECKSUM:
                logger.info("checksum_validation.started", file_id=str(file_id))
                staging_checksum = await verify_staging_object_sha256(str(file_id))
                db_checksum = file_info.get('checksum')

                if staging_checksum == db_checksum:
                    logger.info("checksum_validation.success", file_id=str(file_id))
                    successful_file_ids.append(file_id)
                else:
                    logger.critical("checksum_validation.failed.mismatch", file_id=str(file_id), database_checksum=db_checksum, staging_file_checksum=staging_checksum)
                    validation_failures.append({ "file_id": file_id, "db_checksum": db_checksum, "staging_checksum": staging_checksum })
            else:
                logger.info("checksum_validation.skipped", file_id=str(file_id))
                successful_file_ids.append(file_id)

        except Exception as e:
            logger.error("batch_transfer.task.exception", file_id=str(file_id), message_id=message_id, exc_info=True)
            hard_failures.append({"itemIdentifier": message_id})
            
    return successful_file_ids, validation_failures, hard_failures

async def update_database_records(
    successful_ids: List[UUID],
    validation_failures: List[Dict[str, Any]],
    db_pool: asyncpg.Pool
) -> Tuple[bool, bool]:
    """Concurrently updates the database for successful and validation-failed files."""
    if not successful_ids and not validation_failures:
        return True, True

    async def _update_success():
        if not successful_ids: return True
        async with db_pool.acquire() as conn:
            await safely_advance_file_status_batch(conn, successful_ids, 'distributed')
        return True

    async def _update_failures():
        if not validation_failures: return True
        async with db_pool.acquire() as conn:
            await update_status_with_checksum_failure(conn, validation_failures)
        return True

    try:
        results = await asyncio.gather(_update_success(), _update_failures(), return_exceptions=True)
        success_ok = not isinstance(results[0], Exception)
        validation_ok = not isinstance(results[1], Exception)
        
        if not success_ok: logger.error("db.update.success_group.failed", error=str(results[0]), file_ids=[str(f) for f in successful_ids])
        if not validation_ok: logger.error("db.update.validation_failure_group.failed", error=str(results[1]), count=len(validation_failures))

        return success_ok, validation_ok
    except Exception as e:
        logger.error("update_database_records.unexpected_error", exc_info=True)
        return False, False

