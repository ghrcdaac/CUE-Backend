import asyncio
import structlog
import json
from logic import validate_cleanup_event, get_upload_status_files, delete_upload_status_files
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
    """Synchronous entrypoint for AWS Lambda."""
    logger.info(f"Received event: {json.dumps(event)}")
    return loop.run_until_complete(async_handler(event, context))

async def async_handler(event, context):
    """Async handler to process one or more events."""
    structlog.contextvars.bind_contextvars(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name
    )

    pool = await get_database_pool()
    if not pool:
        logger.critical("db.pool.unavailable")
        raise RuntimeError("Database connection pool could not be initialized.")


    # 1. Validate Event
    try:
        validated_event = await validate_cleanup_event(event)
    except Exception as e: 
        return {"status_code":400, "body":{"message": str(e)}}

    # 2. Read files from the db that have uploading status.
    try: 
        files = await get_upload_status_files(pool, validated_event)
    except Exception as e:
        return {"status_code":500, "body":{"message": str(e)}}

    # 3. Check to see if there are no file to delete.
    if len(files) == 0: 
        logger.info("upload_status_files.empty")
        return {"status_code":200, "body":{"message": "There are no pending uploads to delete."} }

    # 4. Remove files from db.
    try:
        success = await delete_upload_status_files(pool, files)
        if success: 
            logger.info("upload_status_files.delete.success")
            return {"status_code":200, "body":{"message": "Successfully deleted pending uploads."}}
        else:
            logger.info("upload_status_files.delete.partial_success")
            return {"status_code":206, "body":{"message": "Unable to delete all pending uploads."}} 
    except Exception as e: 
        return {"status_code":500, "body":{"message": str(e)}}
