import boto3
from botocore.exceptions import ClientError 
from uuid import UUID 
import json
import os 
from typing import Dict, List, Any, Optional, Tuple
import structlog
from core.db import get_db_connection
from db import fetch_destinations, fetch_file_metadata, update_status_distributed

logger = structlog.get_logger(__file__)
s3_client = boto3.client('s3')

STAGING_BUCKET = os.environ.get("STAGING_BUCKET", "")

async def parse_sqs_message(message:Dict[str,Any]) -> Optional[Dict[str,Any]]:
    try:
        message_body_str = message.get('body')
        if not message_body_str:
            logger.error("sqs.record.body.missing")
            return None
        return json.loads(message_body_str)
    except json.JSONDecodeError:
        logger.warning(f"sqs.record.body.invalid_json", body=message_body_str)
        return None
    except Exception as e:
        logger.error(f"sqs.record.parse_failed", exc_info=True)
        return None

async def process_messages(records) -> Tuple[Dict[str,Dict[str,Any]], Dict[UUID,List[UUID]]] :
    collection_file_map = {}
    messages = {}

    for record in records:
        message_id = record["messageId"]
        message_body = await parse_sqs_message(record)
        if not message_body:
           logger.info("process_message.invalid_message_body", message_body=message_body)
           continue
        collection_id = UUID(message_body.get("collection_id"))
        file_id = UUID(message_body.get("file_id"))
        # Add collection_id and file_id if not in mapping else add file_id
        if not collection_file_map.get(collection_id):
            collection_file_map[collection_id] = [file_id]
        else:
            collection_file_map[collection_id].append(file_id)
        # Map message_id to message
        messages[message_id] = message_body

    return (messages, collection_file_map)

async def copy_file_to_dest(src_bucket:str, src_key:str, dest_bucket:str, dest_key:str) -> Optional[Dict[str,Any]]:
    copy_source = {"Bucket": src_bucket, "Key": src_key}
    try:
        response = s3_client.copy_object(
            CopySource=copy_source,
            Bucket=dest_bucket,
            Key=dest_key,
            ACL="bucket-owner-full-control"
        )
        # If tags need to be remove add TaggingDirective="REPLACE" to copy_object
        # And remove "s3:PutObjectTagging
        logger.info(
            "batch_copy.response", response=response,
            src_bucket=src_bucket, src_key=src_key,
            dest_bucket=dest_bucket, dest_key=dest_key,
            exc_info=True
        )

        return response
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            logger.error(
                "batch_copy.failed.s3_client.no_such_bucket",
                src_bucket=src_bucket, src_key=src_key,
                dest_bucket=dest_bucket, dest_key=dest_key,
                exc_info=True
            )
        elif error_code == 'AccessDenied':
            logger.error(
                "batch_copy.failed.s3_client.access_denied",
                src_bucket=src_bucket, src_key=src_key,
                dest_bucket=dest_bucket, dest_key=dest_key,
                exc_info=True
            )
        elif error_code == 'NoSuchKey':
            logger.error(
                "batch_copy.failed.s3_client.no_such_key",
                src_bucket=src_bucket, src_key=src_key,
                dest_bucket=dest_bucket, dest_key=dest_key,
                exc_info=True
            )
        else:
            logger.error(
                "batch_copy.failed.s3_client.unexpected_client_error",
                src_bucket=src_bucket, src_key=src_key,
                dest_bucket=dest_bucket, dest_key=dest_key,
                exc_info=True
            )
        raise e
    except Exception as e:
        logger.error(
            "batch_copy.failed.unexpected_error",
            src_bucket=src_bucket, src_key=src_key,
            dest_bucket=dest_bucket, dest_key=dest_key,
            exc_info=True
        )
        raise e

async def batch_copy_files(messages:Dict[str, Dict], file_metadata:Dict[UUID,Dict], destinations:Dict[UUID,Dict]) -> Tuple[List[UUID], List[Dict[str,str]]]:
    batch_item_failures = []
    copied_files = []
    for message_id, msg_body in messages.items():
        file_id = UUID(msg_body['file_id'])
        collection_id = UUID(msg_body['collection_id'])
        file_info = file_metadata.get(file_id)
        egress = destinations.get(collection_id)
        # if file has no metadata or egress config
        if not file_info or not egress:
            logger.info(
                "batch_copy.failed.no_file_info_or_egress_config",
                file_id=file_id, collection_id=collection_id,
                file_info=file_info, egress=egress 
            )
            batch_item_failures.append({"itemIdentifier": message_id})
            continue
        collection_path = file_info.get("collection_path")
        name = file_info["name"]
        if collection_path:
            dest_key = os.path.join(collection_path, name)
        else:
            dest_key = name
        egress_path = egress["path"]
        egress_config = egress["config"]
        dest_bucket = egress_config.get("bucket")
        destination_path = egress_config.get("destination_path")
        if not dest_bucket:
            logger.info(
                "batch_copy.failed.no_file_info_or_egress_config",
                file_id=file_id, collection_id=collection_id,
                file_info=file_info, egress=egress 
            )
            batch_item_failures.append({"itemIdentifier": message_id})
            continue
        if destination_path: 
            dest_key = os.path.join(destination_path, name)

        logger.info(f'egress_path:{egress_path}')
        logger.info(f'egress_config:{egress_config}')
        logger.info(f'dest_bucket:{dest_bucket}')
        logger.info(f'dest_key:{dest_key}')
        try:
            await copy_file_to_dest(STAGING_BUCKET, str(file_id), dest_bucket, dest_key)
            copied_files.append(file_id)
        except ClientError as e:
            batch_item_failures.append({"itemIdentifier": message_id})
        except Exception as e:
            logger.info(
                "batch_copy.failed.unexpected",
                file_id=file_id, collection_id=collection_id,
                file_info=file_info, egress=egress 
            )
            batch_item_failures.append({"itemIdentifier": message_id})
    return (copied_files, batch_item_failures)


async def get_collection_egress(collection_ids:List[UUID]) -> Optional[Dict]: 
    try:
        async with get_db_connection() as conn:
            return await fetch_destinations(conn, collection_ids)
    except Exception as e:
        #Error logged in fetch_destinations 
        return None

async def get_file_metadata(file_ids) -> Optional[Dict[UUID, Any]]: 
    try:
        async with get_db_connection() as conn:
            return await fetch_file_metadata(conn, file_ids)
    except Exception as e:
        # Error logged in fetch_file_metadata
        return None

async def update_transferred_files(file_ids) -> bool:
    try:
        async with get_db_connection() as conn:
           return await update_status_distributed(conn, file_ids)
    except Exception as e:
        # Error logged in update_status_distributed 
        return False