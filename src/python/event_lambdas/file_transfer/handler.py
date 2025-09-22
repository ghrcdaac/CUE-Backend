import asyncio
import os
import itertools
import structlog
from typing import Dict,List,Any
from uuid import UUID

from core.logging_config import setup_logging
from core.db_pool import get_database_pool
from logic import (
    process_messages,
    get_collection_egress,
    get_file_metadata,
    batch_copy_files,
    update_successful_transfers,
    update_failed_validations
) 

setup_logging()
logger = structlog.get_logger(__name__)

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

def handler(event, context) -> Dict[str, List[Dict[str,str]]]:
    """Synchronous handler to start asynchronous handler"""
    return loop.run_until_complete(async_handler(event, context))

async def async_handler(event, context) -> Dict[str, List[Dict[str, str]]]:
    """Asynchronous handler to batch process messages"""
    structlog.contextvars.bind_contextvars(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name
    )

    pool = await get_database_pool()
    if not pool:
        logger.critical("db.pool.not_available.failing_invocation")
        failures = [{"itemIdentifier": record["messageId"]} for record in event.get('Records', [])]
        return {"batchItemFailures": failures}

    records = event.get('Records', [])
    batch_item_failures = []

    messages, collection_file_map = await process_messages(records)
    if not messages:
        logger.info("sqs.batch.no_valid_messages")
        return {"batchItemFailures": batch_item_failures}
    
    collection_ids = list(collection_file_map.keys())
    file_ids = list(itertools.chain.from_iterable(collection_file_map.values()))

    destinations = await get_collection_egress(collection_ids, pool)
    file_metadata = await get_file_metadata(file_ids, pool)
    
    if not destinations or not file_metadata:
        batch_item_failures.extend([{"itemIdentifier": msg_id} for msg_id in messages.keys()])
        logger.error("db.batch_queries.no_data", batch_item_failures=batch_item_failures)
        return {"batchItemFailures": batch_item_failures}

    # --- Call the updated copy function and handle its new return signature ---
    successful_ids, validation_failures, hard_failures = await batch_copy_files(messages, file_metadata, destinations)
    batch_item_failures.extend(hard_failures)

    # --- Run both database update tasks concurrently ---
    update_tasks = [
        update_successful_transfers(successful_ids, pool),
        update_failed_validations(validation_failures, pool)
    ]
    results = await asyncio.gather(*update_tasks)
    
    # Check the results of the two update tasks separately for granular retries.
    success_update_ok, validation_update_ok = results
    
    # If the DB update for successfully validated files failed, mark their messages for retry.
    if not success_update_ok:
        logger.error("db.update.failed.success_group", file_ids=[str(f) for f in successful_ids])
        for msg_id, body in messages.items():
            if UUID(body['file_id']) in successful_ids:
                batch_item_failures.append({"itemIdentifier": msg_id})

    # If the DB update for checksum-failed files failed, mark their messages for retry.
    if not validation_update_ok:
        vf_ids = {vf['file_id'] for vf in validation_failures}
        logger.error("db.update.failed.validation_failure_group", file_ids=[str(f) for f in vf_ids])
        for msg_id, body in messages.items():
            if UUID(body['file_id']) in vf_ids:
                batch_item_failures.append({"itemIdentifier": msg_id})
            
    logger.info("sqs.batch.batchItemFailures", batch_item_failures=batch_item_failures)
    logger.info("sqs.batch.success")  

    return {"batchItemFailures": batch_item_failures}

