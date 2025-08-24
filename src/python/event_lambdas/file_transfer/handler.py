# ./src/python/event_lambdas/file_transfer/handler.py
import asyncio
import logging
import os
import itertools
from typing import Dict,List

from lambda_utils.database_util.db_util import get_connection_pool

from .db import fetch_file_metadata, update_status_distributed
from .logic import process_messages, get_collection_egress, batch_copy_files #get_redis_client

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))

def handler(event, context) -> Dict[str, List[str]]:
    """Synchronous handler to start asynchronous handler"""
    return asyncio.run(async_handler(event, context))

async def async_handler(event, context) -> Dict[str, List[str]]:
    """Asynchronous handler batch process messages"""
    logger.info(f"processing {event}")
    records = event.get('Records', [])

    batch_item_failures = []
    # Map collections to files and messageIds to message bodies
    messages, collection_file_map = await process_messages(records)
    # Create list of collection_ids and file_ids for bulk queries
    collection_ids = list(collection_file_map.keys())
    file_ids = list(itertools.chain.from_iterable(collection_file_map.values()))

    pool = await get_connection_pool()
    #redis_client = await get_redis_client()
    try:
        async with pool.acquire() as conn:
            destinations = await get_collection_egress(conn, collection_ids)# redis_client,
            # if no destinations cannot proceed with file transfer
            if not destinations:
               batch_item_failures.extend([{"itemIdentifier": message_id} for message_id in messages.keys()])
               return {"batchItemFailures": batch_item_failures}
            file_metadata = await fetch_file_metadata(conn, file_ids)
            # if no file metadata cannot proceed with file transfer
            if not file_metadata:
               batch_item_failures.extend([{"itemIdentifier": message_id} for message_id in messages.keys()])
               return {"batchItemFailures": batch_item_failures}
    except Exception as e:
        logger.error(f"Error gathering required information from database: {e}", exc_info=True)
        batch_item_failures.extend([{"itemIdentifier": message_id} for message_id in messages.keys()])
        return {"batchItemFailures": batch_item_failures}
    finally:
       await pool.close()

    copied_files = []
    copied_files, failed_to_copy = await batch_copy_files(messages, file_metadata, destinations)
    batch_item_failures.extend(failed_to_copy)

    pool = await get_connection_pool()
    try:
        async with pool.acquire() as conn:
            await update_status_distributed(conn, copied_files)
    except Exception as e:
        logger.error(f"Error occurred while update file statuses to distributed {e}")
        logger.error(f"Failed to update status for these files: {copied_files}")
    finally:
        await pool.close()

    logger.info(f"batchItemFailures: {batch_item_failures}")

    return {"batchItemFailures": batch_item_failures}
