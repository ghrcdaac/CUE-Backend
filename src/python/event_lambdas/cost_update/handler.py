from datetime import datetime, timedelta
import asyncio
import json
import os
from logic import update_file_costs
from core.db_pool import get_database_pool
import structlog

logger = structlog.get_logger(__name__)

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

def handler(event, context):
    """Synchronous entrypoint for AWS Lambda."""
    logger.info(f"Received event: {json.dumps(event)}")
    return loop.run_until_complete(async_handler(event, context))

async def async_handler(event, context):
    """Async handler to process one or more events."""
    structlog.contextvars.bind_contextvars(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name
    )

    return await process_event(event)

async def process_event(event):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    pool = await get_database_pool()
    try:
        await update_file_costs(start_date, end_date, pool)
        logger.info("Finished updating yesterday's files with cost")
    except Exception as e:
        logger.error("Failed to update cost", exc_info=True)
        raise e

