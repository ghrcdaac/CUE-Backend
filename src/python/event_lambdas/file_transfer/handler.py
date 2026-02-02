import asyncio
import structlog
from typing import Dict, List
from uuid import UUID

from core.logging_config import setup_logging
from core.db_pool import get_database_pool
from .logic import (
    process_messages,
    batch_transfer_and_validate,
    update_database_records
)
from .db import fetch_batch_transfer_details

setup_logging()
logger = structlog.get_logger(__name__)

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

def handler(event, context) -> Dict[str, List[Dict[str, str]]]:
    """Synchronous entry point for AWS Lambda."""
    return loop.run_until_complete(async_handler(event, context))

async def async_handler(event, context) -> Dict[str, List[Dict[str, str]]]:
    """Asynchronous handler to batch process messages."""
    structlog.contextvars.bind_contextvars(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name
    )

    pool = await get_database_pool()
    if not pool:
        logger.critical("db.pool.unavailable")
        failures = [{"itemIdentifier": record["messageId"]} for record in event.get('Records', [])]
        return {"batchItemFailures": failures}

    messages, file_ids = await process_messages(event.get('Records', []))
    if not messages:
        return {"batchItemFailures": []}

    # This single database call now gets all required info for the batch.
    async with pool.acquire() as conn:
        transfer_details = await fetch_batch_transfer_details(conn, file_ids)
    
    # Transfer files, validate them, and categorize the results.
    successful_ids, validation_failures, hard_failures = await batch_transfer_and_validate(messages, transfer_details)

    # Concurrently update statuses for successful and validation-failed files.
    success_update_ok, validation_update_ok = await update_database_records(successful_ids, validation_failures, pool)

    batch_item_failures = list(hard_failures)
    
    # If DB updates failed, mark corresponding SQS messages for retry.
    if not success_update_ok:
        for msg_id, body in messages.items():
            if UUID(body['file_id']) in successful_ids:
                batch_item_failures.append({"itemIdentifier": msg_id})
                
    if not validation_update_ok:
        vf_ids = {vf['file_id'] for vf in validation_failures}
        for msg_id, body in messages.items():
            if UUID(body['file_id']) in vf_ids:
                batch_item_failures.append({"itemIdentifier": msg_id})

    logger.info("sqs.batch.complete", success_count=len(successful_ids), validation_fail_count=len(validation_failures), hard_fail_count=len(hard_failures), retry_count=len(batch_item_failures))
    return {"batchItemFailures": batch_item_failures}

