from typing import Dict, List, Any, Optional, Tuple
import boto3
from botocore.exceptions import ClientError 
#from redis.exceptions import RedisError
#from redis.asyncio.client import Redis
#import redis.asyncio as redis
from asyncpg import Connection
from uuid import UUID 
import json
import os 
import logging
from .db import fetch_destinations

logger = logging.getLogger(__file__)
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))
s3_client = boto3.client('s3')

#REDIS_HOST = os.environ.get("REDIS_HOST", "")
#REDIS_PORT = os.environ.get("REDIS_PORT", "6739")
STAGING_BUCKET = os.environ.get("STAGING_BUCKET", "")


#async def get_redis_client(redis_host:str = REDIS_HOST, redis_port:str = REDIS_PORT) -> Redis:
    #try:
        #redis_client = await redis.StrictRedis(
            #host=redis_host,
            #port=int(redis_port),
            #decode_responses=True
        #)
        #return redis_client
    #except RedisError as e: 
        #logger.error(f"Error occurred while getting redis client: {e}", exc_info=True)
        #raise
    #except Exception as e:
        #logger.error(f"An unexpected occurred while getting redis client {e}", exc_info=True)
        #raise

async def parse_sqs_message(message:Dict[str,Any]) -> Optional[Dict[str,Any]]:
    try:
        message_body_str = message.get('body')
        if not message_body_str:
            logger.error("SQS record is missing 'body' field.")
            return None
        return json.loads(message_body_str)
    except json.JSONDecodeError:
        logger.warning(f"Message body is not valid JSON, likely a health check. Body: '{message_body_str}'")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during SQS record parsing: {e}", exc_info=True)
        return None

async def process_messages(records) -> Tuple[Dict[str,Dict[str,Any]], Dict[UUID,List[UUID]]] :
    collection_file_map = {}
    messages = {}

    for record in records:
        message_id = record["messageId"]
        message_body = await parse_sqs_message(record)
        if not message_body:
           logger.info(f"Invalid message_body: {message_body}")
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
        response = s3_client.copy_object(CopySource=copy_source,
                                         Bucket=dest_bucket,
                                         Key=dest_key,
                                         ACL="bucket-owner-full-control")
        # If tags need to be remove add TaggingDirective="REPLACE" to copy_object
        # And remove "s3:PutObjectTagging
        logger.info(f"CopyObject response: {response}")
        return response
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            logger.error(f"Error the one of the buckets does not exist: {e}", exc_info=True)
        elif error_code == 'AccessDenied':
             logger.error(f"Error access denied. Ensure permission to access the bucket and key: {e}", exc_info=True)
        elif error_code == 'NoSuchKey':
             logger.error(f"Error the specified key '{src_key}' does not exist in {src_bucket}: {e}", exc_info=True)
        else:
             logger.error(f"An unexpected s3 client error occurred: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise

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
        dest_bucket = egress_config["bucket"]
        logger.info(f'egress_path:{egress_path}')
        logger.info(f'egress_config:{egress_config}')
        logger.info(f'dest_bucket:{dest_bucket}')
        logger.info(f'dest_key:{dest_key}')
        try:
            await copy_file_to_dest(STAGING_BUCKET, str(file_id), dest_bucket, dest_key)
            copied_files.append(file_id)
        except Exception as e:
            logger.error(f"failed to copy {file_id} to {dest_bucket}: {e}")
            batch_item_failures.append({"itemIdentifier": message_id})
    return (copied_files, batch_item_failures)

#async def get_destinations_cache(collection_ids:List[UUID]):#redis_client: Redis, collection_ids:List[UUID]) -> Optional[Dict[UUID,Any]]:
    #try:
        #results = await redis_client.mget(collection_ids)
        #if any(result is None for result in results):
            #return None
        #collection_egress_map = dict(zip(collection_ids, results))
        #return collection_egress_map
    #except RedisError as e:
        #logger.error(f"Error getting collection egress from cache: {e}", exc_info=True)
        #return None
    #except Exception as e:
        #logger.error(f"An unexpected error occurred while getting collection egress from cache {e}", exc_info=True)
        #return None


#async def set_destinations_cache(redis_client:Redis, collection_egress_map:[UUID,Any]) -> bool:
    #try:
        #for collection_id, egress_data in collection_egress_map:
            #await redis_client.set(collection_id, egress_data, ex=86400) #expire in 24 hours
        #logger.info("Set collection egress to cache")
        #return True
    #except RedisError as e:
        #logger.error(f"Error setting collection egress to cache: {e}", exc_info=True)
        #return False
    #except Exception as e:
        #logger.error(f"An unexpected error occurred while setting collection egress in cache: {e}", exc_info=True)
        #return False


async def get_collection_egress(conn:Connection, collection_ids:List[UUID]) -> Optional[Dict]: #redis_client:Redis, conn: Connection, collection_ids:List[UUID]) -> Optional[Dict]:
    try:
        #results = await get_destinations_cache(redis_client, collection_ids)
        #if not results:
        results = await fetch_destinations(conn, collection_ids)
        if not results:
            return None
        #success = set_destinations_cache(redis_client, results)
        #if not success:
        #logger.warning("collection egress did not update successfully")
        return results
    except Exception as e:
        logger.error(f"Error not able to get collection egress from cache or database: {e}", exc_info=True)
        raise
