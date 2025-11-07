from datetime import datetime, timedelta, timezone
import asyncio
import json
import os 
from logic import update_file_costs
from core.db_pool import get_database_pool
import structlog

logger = structlog.get_logger(__name__)
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", 1))

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
    start_time = event.get("start_time")
    end_time = event.get("end_time")
    # If start_time or end_time is not present
    # default to the current datetime(utc) for end_time
    # and the previous day for the start_time
    try: 
        if end_time is None:
            end_time = datetime.now(tz=timezone.utc)
        else:
            end_time = datetime.fromisoformat(end_time).replace(tzinfo=timezone.utc)

        if start_time is None:
            start_time = end_time - timedelta(days=LOOKBACK_DAYS)
            start_time = start_time.replace(tzinfo=timezone.utc)
        else:
            start_time = datetime.fromisoformat(start_time).replace(tzinfo=timezone.utc)
    except ValueError as e:
        logger.error("start_time or end_time does not follow ISO 8601 format.")
        raise e
    if not start_time <= end_time:
        raise ValueError("start_time must come before or be the same as end_time")

    return await update_costs(start_time, end_time)

async def update_costs(start_time:datetime, end_time:datetime):
    pool = await get_database_pool()
    try:
        await update_file_costs(start_time, end_time, pool)
        logger.info(f"Finished updating files between {start_time} - {end_time} with cost")
    except Exception as e:
        logger.error("Failed to update cost", exc_info=True)
        raise e

