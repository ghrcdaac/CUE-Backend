from datetime import datetime, timedelta
import asyncio
import json
import os
from .logic import update_file_costs
import logging

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

async def process_event(event):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    try:
        await update_file_costs(start_date, end_date)
        logger.info("Finished updating yesterday's files with cost")
    except Exception as e:
        logger.error("Failed to update cost", exc_info=True)
        raise e

async def async_handler(event, context):
    """Async handler to process one or more events."""
    await process_event(event)

def handler(event, context):
    """Synchronous entrypoint for AWS Lambda."""
    logger.info(f"Received event: {json.dumps(event)}")
    return asyncio.run(async_handler(event, context))