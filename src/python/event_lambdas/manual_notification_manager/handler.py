import asyncio
import structlog
import boto3
from logic import validate_notification, invoke_notification_manager, ManualNotificationError

from core.logging_config import setup_logging
from core.db_pool import get_database_pool

setup_logging()
logger = structlog.get_logger(__name__)

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
lambda_client = boto3.client('lambda')

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

    # 1. Validate notification
    pool = await get_database_pool()
    if not pool:
        logger.critical("db.pool.unavailable")
        raise RuntimeError("Database connection pool could not be initialized.")
     
    try:
        notification = await validate_notification(pool, event) 
    except ManualNotificationError as e:
        return  {
            "status_code": 400,
            "body":{"message": f"Invalid Notification: {str(e)}"}
        }
    
    # 2. Invoke notification_manager
    try: 
        await invoke_notification_manager(notification.detail_type, notification.detail)
        return {
            "body": {
                "status_code": 200,
                "message": "Successfully invoked notification_manager"
            }
        }
    except ManualNotificationError as e:
        return {
            "body": {
                "status_code": 500,
                "message": "Failed to invoke notification_manager"
            }
        }

