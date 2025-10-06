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
# Environment variable to control checksum validation
VERIFY_CHECKSUM = os.environ.get("VERIFY_CHECKSUM_ON_TRANSFER", "true").lower() == "true"


async def parse_sqs_message(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
    """Parses SQS records and extracts file IDs for batch processing."""
    messages = {}
    file_ids = []
    for record in records:
        message_id = record["messageId"]
        message_body = await parse_sqs_message(record)
        if not message_body or not message_body.get("file_id"):
            logger.warning("process_message.skip.invalid_body", message_id=message_id)
            continue
        
        messages[message_id] = message_body
        file_ids.append(UUID(message_body["file_id"]))
        
    return messages, file_ids

async def verify_staging_object_sha256(file_id: str) -> str:
    """Downloads an S3 object from the staging bucket and computes its SHA256 hash."""
    sha256_hash = hashlib.sha256()
    
    async def download_and_hash():
        try:
            response = s3_client.get_object(Bucket=STAGING_BUCKET, Key=file_id)
            body = response['Body']
            for chunk in body.iter_chunks(chunk_size=8192 * 1024):
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
    retry_delay_base = 2  # seconds

    for attempt in range(max_retries):
        try:
            await asyncio.to_thread(
                s3_client.copy_object,
                CopySource=copy_source,
                Bucket=dest_bucket,
                Key=dest_key,
                ACL="bucket-owner-full-control"
            )
            # Add detailed log on success
            logger.info(
                "s3.copy.success",
                file_id=src_key,
                source_bucket=STAGING_BUCKET,
                source_key=src_key,
                dest_bucket=dest_bucket,
                dest_key=dest_key
            )
            return  # Success, exit the function
        except ClientError as e:
            if e.response['Error']['Code'] in ['ServiceUnavailable', 'SlowDown', 'InternalError'] and attempt < max_retries - 1:
                delay = retry_delay_base * (2 ** attempt)
                logger.warning("s3.copy.transient_error.retrying", attempt=attempt + 1, max_retries=max_retries, file_id=src_key, delay=delay)
                await asyncio.sleep(delay)
            else:
                logger.error("s3.copy.failed.persistent_error", src_key=src_key, dest_key=dest_key, error_code=e.response['Error']['Code'])
                raise  # Re-raise the exception after the last attempt or for non-retryable errors

async def batch_transfer_and_validate(
    messages: Dict[str, Dict],
    transfer_details: Dict[UUID, Dict]
) -> Tuple[List[UUID], List[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Transfers files, optionally validates them based on environment config, and categorizes results.
    Returns: (successful_ids, validation_failures, hard_failures)
    """
    hard_failures = []
    successful_file_ids = []
    validation_failures = []

    for message_id, msg_body in messages.items():
        file_id = UUID(msg_body['file_id'])
        details = transfer_details.get(file_id)

        if not details:
            logger.warning("batch_transfer.skip.no_metadata_or_not_ready", file_id=str(file_id),
                         detail="File may be missing, or its name/checksum may still be 'pending'.")
            # This is not a hard failure for SQS, as the file might be ready on the next run.
            continue

        file_info = details["file_info"]
        egress = details["egress"]
        dest_bucket = egress.get("config", {}).get("bucket")

        if not dest_bucket:
            logger.error("batch_transfer.failed.no_destination_bucket", file_id=str(file_id))
            hard_failures.append({"itemIdentifier": message_id})
            continue

        # Safely construct the destination path
        path_parts = [p for p in [egress.get("config", {}).get("destination_path"), file_info.get("collection_path"), file_info["name"]] if p]
        dest_key = os.path.join(*path_parts)

        try:
            # Step 1: Transfer the file first. This includes the retry logic.
            await copy_file_to_dest(str(file_id), dest_bucket, dest_key)

            # Step 2: Optionally validate checksum.
            if VERIFY_CHECKSUM:
                staging_checksum = await verify_staging_object_sha256(str(file_id))
                db_checksum = file_info.get('checksum')

                if staging_checksum == db_checksum:
                    successful_file_ids.append(file_id)
                else:
                    logger.critical(
                        "checksum_mismatch",
                        file_id=str(file_id),
                        database_checksum=db_checksum,
                        staging_file_checksum=staging_checksum
                    )
                    validation_failures.append({
                        "file_id": file_id,
                        "db_checksum": db_checksum,
                        "staging_checksum": staging_checksum
                    })
            else:
                # If validation is skipped, the transfer is considered successful.
                successful_file_ids.append(file_id)

        except Exception:
            logger.error("batch_transfer.task.exception", file_id=str(file_id), message_id=message_id, exc_info=True)
            hard_failures.append({"itemIdentifier": message_id})
            
    return successful_file_ids, validation_failures, hard_failures

async def update_database_records(
    successful_ids: List[UUID],
    validation_failures: List[Dict[str, Any]],
    db_pool: asyncpg.Pool
) -> Tuple[bool, bool]:
    """Runs the two database update tasks concurrently and returns their success status."""
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
        results = await asyncio.gather(
            _update_success(),
            _update_failures(),
            return_exceptions=True
        )
        success_ok = not isinstance(results[0], Exception)
        validation_ok = not isinstance(results[1], Exception)
        
        if not success_ok: logger.error("db.update.success_group.failed", error=str(results[0]))
        if not validation_ok: logger.error("db.update.validation_failure_group.failed", error=str(results[1]))

        return success_ok, validation_ok
    except Exception as e:
        logger.error("update_database_records.unexpected_error", exc_info=True)
        return False, False

