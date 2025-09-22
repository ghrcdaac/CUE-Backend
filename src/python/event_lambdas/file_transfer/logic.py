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


from db import fetch_destinations, fetch_file_metadata, update_status_distributed, update_status_with_checksum_failure

logger = structlog.get_logger(__file__)
s3_client = boto3.client('s3')

STAGING_BUCKET = os.environ.get("STAGING_BUCKET", "")


async def parse_sqs_message(message:Dict[str,Any]) -> Optional[Dict[str,Any]]:
    try:
        message_body_str = message.get('body')
        if not message_body_str:
            logger.error("sqs.record.body.missing", record_id=message.get("messageId"))
            return None
        return json.loads(message_body_str)
    except json.JSONDecodeError:
        logger.warning(f"sqs.record.body.invalid_json", body=message_body_str, record_id=message.get("messageId"))
        return None
    except Exception as e:
        logger.error(f"sqs.record.parse_failed", exc_info=True, record_id=message.get("messageId"))
        return None

async def process_messages(records) -> Tuple[Dict[str,Dict[str,Any]], Dict[UUID,List[UUID]]] :
    collection_file_map = {}
    messages = {}

    for record in records:
        message_id = record["messageId"]
        message_body = await parse_sqs_message(record)
        if not message_body:
            logger.warning("process_message.skip.invalid_body", message_id=message_id)
            continue
        
        collection_id_str = message_body.get("collection_id")
        file_id_str = message_body.get("file_id")
        if not collection_id_str or not file_id_str:
            logger.error(
                "process_message.skip.missing_ids",
                message_id=message_id,
                has_collection_id=(collection_id_str is not None),
                has_file_id=(file_id_str is not None)
            )
            continue
            
        collection_id = UUID(collection_id_str)
        file_id = UUID(file_id_str)
        
        if not collection_file_map.get(collection_id):
            collection_file_map[collection_id] = [file_id]
        else:
            collection_file_map[collection_id].append(file_id)
        
        messages[message_id] = message_body

    return (messages, collection_file_map)

async def verify_staging_object_sha256(file_id: str) -> str:
   
    sha256_hash = hashlib.sha256()
    
    def download_and_hash():
        try:
            response = s3_client.get_object(Bucket=STAGING_BUCKET, Key=file_id)
            body = response['Body']
            for chunk in body.iter_chunks(chunk_size=8192 * 1024):
                sha256_hash.update(chunk)
        except ClientError as e:
            logger.error(
                "s3.get_object.failed_from_staging",
                bucket=STAGING_BUCKET,
                key=file_id,
                error_code=e.response['Error']['Code'],
                exc_info=True
            )
            raise

    await asyncio.to_thread(download_and_hash)
    
    return base64.b64encode(sha256_hash.digest()).decode('utf-8')

async def copy_file_to_dest(src_bucket:str, src_key:str, dest_bucket:str, dest_key:str):
    
    copy_source = {"Bucket": src_bucket, "Key": src_key}
    try:
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=dest_bucket,
            Key=dest_key,
            ACL="bucket-owner-full-control"
        )
    except ClientError as e:
        logger.error(
            "s3.copy.failed.client_error",
            src_bucket=src_bucket, src_key=src_key,
            dest_bucket=dest_bucket, dest_key=dest_key,
            error_code=e.response['Error']['Code'],
            exc_info=True
        )
        raise

# ---  This function now separates successful files from checksum failures ---
async def batch_copy_files(
    messages: Dict[str, Dict],
    file_metadata: Dict[UUID, Dict],
    destinations: Dict[UUID, Dict]
) -> Tuple[List[UUID], List[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Transfers files, validates them, and categorizes results.
    Returns: (successful_ids, validation_failures, hard_failures)
    """
    hard_failures = []
    successful_file_ids = []
    validation_failures = []

    for message_id, msg_body in messages.items():
        file_id = UUID(msg_body['file_id'])
        collection_id = UUID(msg_body['collection_id'])
        file_info = file_metadata.get(file_id)
        egress = destinations.get(collection_id)

        if not file_info or not egress:
            logger.error("batch_copy.failed.no_metadata", file_id=str(file_id), has_info=(file_info is not None), has_egress=(egress is not None))
            hard_failures.append({"itemIdentifier": message_id})
            continue

        dest_bucket = egress.get("config", {}).get("bucket")
        if not dest_bucket:
            logger.error("batch_copy.failed.no_destination_bucket", file_id=str(file_id), egress_config=egress.get("config"))
            hard_failures.append({"itemIdentifier": message_id})
            continue

        file_name = file_info["name"]
        collection_path = file_info.get("collection_path")
        destination_path = egress.get("config", {}).get("destination_path")
        
        dest_key_parts = [p for p in [destination_path, collection_path, file_name] if p]
        dest_key = os.path.join(*dest_key_parts)

        try:
            # 1. Transfer the file FIRST to ensure delivery.
            await copy_file_to_dest(STAGING_BUCKET, str(file_id), dest_bucket, dest_key)
            logger.info("s3.copy.success", file_id=str(file_id), dest_bucket=dest_bucket, dest_key=dest_key)

            # 2. Then, perform the validation.
            logger.info("s3.pre_transfer_validation.started", file_id=str(file_id))
            staging_checksum = await verify_staging_object_sha256(str(file_id))
            db_checksum = file_info.get('checksum')

            # 3. Categorize the result based on the validation.
            if staging_checksum == db_checksum:
                logger.info("s3.pre_transfer_validation.success", file_id=str(file_id))
                successful_file_ids.append(file_id)
            else:
                logger.critical(
                    "s3.pre_transfer_validation.checksum_mismatch",
                    file_id=str(file_id),
                    database_checksum=db_checksum,
                    staging_file_checksum=staging_checksum
                )
                validation_failures.append({
                    "file_id": file_id,
                    "db_checksum": db_checksum,
                    "staging_checksum": staging_checksum
                })
        
        except Exception as e:
            logger.error(
                "batch_copy.task.failed_with_exception",
                file_id=str(file_id),
                message_id=message_id,
                exception_type=type(e).__name__,
                exc_info=True
            )
            hard_failures.append({"itemIdentifier": message_id})
            
    return (successful_file_ids, validation_failures, hard_failures)

async def get_collection_egress(collection_ids: List[UUID], db_pool: asyncpg.Pool) -> Optional[Dict]: 

    try:
        async with db_pool.acquire() as conn:
            return await fetch_destinations(conn, collection_ids)
    except Exception as e:
        logger.error("get_collection_egress.unexpected_error", exc_info=True)
        return None

async def get_file_metadata(file_ids: List[UUID], db_pool: asyncpg.Pool) -> Optional[Dict[UUID, Any]]: 

    try:
        async with db_pool.acquire() as conn:
            return await fetch_file_metadata(conn, file_ids)
    except Exception as e:
        logger.error("get_file_metadata.unexpected_error", exc_info=True)
        return None


async def update_successful_transfers(file_ids: List[UUID], db_pool: asyncpg.Pool) -> bool:
    """Updates the status for files that were successfully transferred and validated."""
    if not file_ids:
        return True
    try:
        async with db_pool.acquire() as conn:
            return await update_status_distributed(conn, file_ids)
    except Exception as e:
        logger.error("update_successful_transfers.unexpected_error", exc_info=True)
        return False

async def update_failed_validations(failure_details: List[Dict[str, Any]], db_pool: asyncpg.Pool) -> bool:
    """Updates the status and logs checksum errors for files that were transferred but failed validation."""
    if not failure_details:
        return True
    try:
        async with db_pool.acquire() as conn:
            return await update_status_with_checksum_failure(conn, failure_details)
    except Exception as e:
        logger.error("update_failed_validations.unexpected_error", exc_info=True)
        return False

