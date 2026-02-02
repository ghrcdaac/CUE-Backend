import asyncio
import structlog
from .logic import validate_files, poll_and_redrive

from core.logging_config import setup_logging
from core.db_pool import get_database_pool

setup_logging()
logger = structlog.get_logger(__name__)

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

def handler(event, context):
    """Synchronous entry point for AWS Lambda."""
    return loop.run_until_complete(async_handler(event, context))

async def async_handler(event, context):
    """Asynchronous handler to batch process messages."""
    structlog.contextvars.bind_contextvars(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name
    )

    logger.info(full_event=event) 

    pool = await get_database_pool()
    if not pool:
        logger.critical("db.pool.unavailable")
        raise RuntimeError("Database connection pool could not be initialized.")

    # 1. Validate file_ids 
    valid_file_ids, invalid_file_ids = await validate_files(pool, event)

    # 2. Extract messages associated to message ids
    try:
        results = await poll_and_redrive(valid_file_ids)
        not_redriven = results["not_redriven"]
        moved_total = results["moved_total"]
        errors_total = results["errors_total"]

        if len(not_redriven) == 0:
            status_code = 200
            message = f"Redrive complete: moved={moved_total} errors={errors_total}."
        elif moved_total > 0:
            status_code = 200  # Partial success 
            message = f"Partial redrive: moved={moved_total} errors={errors_total}."
        else:
            status_code = 500 if errors_total > 0 else 404
            reason = "Requested file_ids not found." if status_code == 404 else "Processing failed."
            message = f"No messages redriven: moved={moved_total}, errors={errors_total}. {reason}"

        return {
            "status_code": status_code,
            "body":{
                "message": message,
                "file_ids_not_redriven": not_redriven,
                "invalid_file_ids": invalid_file_ids
            }
        }

    except Exception as e:
        logger.info("redrive_failed.unrecoverable_error")
        return {
            "status_code": 500,
            "body": {
                "message": str(e),
                "file_ids_not_redriven": event.get("file_ids") if isinstance(event.get("file_ids"), list) else []
            }
        }