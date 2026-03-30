import asyncio
import os
import structlog
import boto3
from botocore.exceptions import ClientError
from uuid import UUID
import json
from .db import get_collection_id, validate_clean_file
from .model import Event
from pydantic import ValidationError

from core.logging_config import setup_logging
from core.db_pool import get_database_pool

setup_logging()
logger = structlog.get_logger(__name__)

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

STAGING_BUCKET = os.environ.get("STAGING_BUCKET")
CLEAN_FILES_QUEUE_URL = os.environ.get("QUEUE_URL")

def _get_s3_client():
    return boto3.client("s3")

def handler(event, context):
    """Synchronous entry point for AWS Lambda."""
    return loop.run_until_complete(async_handler(event, context))

async def async_handler(event, context):
    """Asynchronous handler to batch process messages."""
    structlog.contextvars.bind_contextvars(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name
    )

    transferable_file_ids = [] # file_ids of files that will be sent to clean file queue for transfer
    not_found_file_ids = [] # file_ids of files that do not exist in the staging bucket
    invalid_status_file_ids = [] # file_ids of files that do not a clean status

    # 1. Parse file_id list from input
    try:
        parsed_event = Event(**event)
        file_ids = parsed_event.file_ids
    except ValidationError as e:
        logger.error("file_ids.parsing.failed", error=e)
        return {
            "status_code":400,
            "body":{"message":"Invalid File IDs"}
        } # not able to process either empty or invalid 

    pool = await get_database_pool()
    if not pool:
        logger.critical("db.pool.unavailable")
        raise RuntimeError("Database connection pool could not be initialized.")


    # 2. For each file_id perform checks
    #    file must be clean # The  file must exist in the clean scan queue
    async with pool.acquire() as conn:
        for file_id in file_ids:
            exists = await exists_in_staging(file_id)
            if not exists:
                not_found_file_ids.append(file_id)
                continue

            clean = await validate_clean_file(conn, file_id)
            if not clean:
                invalid_status_file_ids.append(file_id)
                logger.info('file_id.status.not_clean', file_id=file_id)
                continue

            transferable_file_ids.append(file_id)

    # 3. For each transferable file_id find the associated collection_id
    #    Create a JSON message and send message to clean file SQS queue
    failed_files = []
    if len(transferable_file_ids) > 0:
        logger.info("file_ids.transfer_file_ids", transferable_file_ids=transferable_file_ids)
        sqs_client = boto3.client("sqs")
        async with pool.acquire() as conn:
            for file_id in transferable_file_ids:
                collection_id = await get_collection_id(conn, file_id)
                msg = {"file_id": str(file_id), "collection_id": str(collection_id)}
                try:
                    sqs_client.send_message(
                        QueueUrl=CLEAN_FILES_QUEUE_URL,
                        MessageBody=json.dumps(msg)
                    )
                except ClientError as e:
                    logger.error("sqs.send_message.failed", file_id=file_id, error=e)
                    failed_files.append(file_id)
        transferable_file_ids = [file_id for file_id in transferable_file_ids if file_id not in failed_files]
        failed_files = [{"file_id": str(file_id), "message":"Failed to submit file for transfer."} for file_id in failed_files]

    # 4. If there are any not found or invalid status failures add them 
    #    to the failed_files list.
    num_not_found = len(not_found_file_ids)
    num_invalid_status = len(invalid_status_file_ids)

    if num_not_found > 0 or num_invalid_status > 0:
        failed_files.extend([{"file_id": str(file_id), "message":"Does not exist in staging bucket."} for file_id in not_found_file_ids])
        failed_files.extend([{"file_id": str(file_id), "message":"Is not clean."} for file_id in invalid_status_file_ids])

    total_files = len(file_ids)
    num_failed_files = len(failed_files)

    if num_failed_files > 0 and num_failed_files < total_files:
        return {"status_code":207, "body":{"file_ids":json.dumps(failed_files)}}
    elif num_failed_files == total_files:
        logger.info('failed_file_ids', file_ids=failed_files)
        return {"status_code":400, "body":{"file_ids":json.dumps(failed_files)}}
    else:
        return {"status_code":200, "body":{"message":"All file transfers initiated."}}

async def exists_in_staging(file_id:UUID):
    """Checks the existence of the file in the staging bucket"""
    try:
       s3 = _get_s3_client()
       result = s3.head_object(Bucket=STAGING_BUCKET, Key=str(file_id))
       if result:
           logger.info('file_id.staging_bucket.exists', file_id=file_id)
           return True
    except ClientError as e:
        logger.error('file_id.staging_bucket.client_error', file_id=file_id, error=e)
        return False
