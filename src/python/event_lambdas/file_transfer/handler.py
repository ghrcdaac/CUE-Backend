# ./src/python/event_lambdas/file_transfer/handler.py
import asyncio
import os
import itertools
import structlog
from typing import Dict,List,Any

from core.logging_config import setup_logging
from logic import (
    process_messages,
    get_collection_egress,
    get_file_metadata,
    batch_copy_files,
    update_transferred_files
) 

setup_logging()
logger = structlog.get_logger(__name__)

def handler(event, context) -> Dict[str, List[Dict[str,str]]]:
    """Synchronous handler to start asynchronous handler"""
    return asyncio.run(async_handler(event, context))

async def async_handler(event, context) -> Dict[str, List[Dict[str, str]]]:
    """Asynchronous handler batch process messages"""
    structlog.contextvars.bind_contextvars(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name
    )

    records = event.get('Records', [])
    batch_item_failures = []

    # Map collections to files and messageIds to message bodies
    messages, collection_file_map = await process_messages(records)
    if not messages: # No valid messages should return, return empty list no further processing. 
       logger.info("sqs.batch.no_valid_messages")
       return {"batchItemFailures": batch_item_failures}
    
    # Create list of collection_ids and file_ids for bulk queries
    collection_ids = list(collection_file_map.keys())
    file_ids = list(itertools.chain.from_iterable(collection_file_map.values()))

    # Get collection egress and file metadata for copying
    destinations = await get_collection_egress(collection_ids)
    file_metadata = await get_file_metadata(file_ids)
    # If either destinations or file_metadata is not found then processing cannot continue
    if not destinations or not file_metadata:
        batch_item_failures.extend([{"itemIdentifier": msg_id} for msg_id in messages.keys()])
        logger.info("db.batch_queries.no_data", batch_item_failures=batch_item_failures)
        return {"batchItemFailures": batch_item_failures}

    # Copy files
    # Add failed copies to batch item failures for reprocessing,
    # Update successful copies with distributed status and egress time
    copied_files, failed_to_copy = await batch_copy_files(messages, file_metadata, destinations)
    batch_item_failures.extend(failed_to_copy)
    success = await update_transferred_files(copied_files)
    if not success:
        batch_item_failures = []
        batch_item_failures = [{"itemIdentifier": msg_id} for msg_id in messages.keys()]
        return {"batchItemFailures": batch_item_failures}
           
    logger.info("sqs.batch.batchItemFailures", batch_item_failures=batch_item_failures)
    logger.info("sqs.batch.success")  

    return {"batchItemFailures": batch_item_failures}
