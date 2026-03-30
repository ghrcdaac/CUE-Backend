import asyncio
import structlog
import boto3
from logic import validate_time_range, invoke_cost_update, ManualCostUpdateError

from core.logging_config import setup_logging

setup_logging()
logger = structlog.get_logger(__name__)

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

lambda_client = boto3.client("lambda")

def handler(event, context):
    """Synchronous entry point for AWS Lambda."""
    return loop.run_until_complete(async_handler(event, context))

async def async_handler(event, context):
    """Asynchronous handler to batch process messages."""
    structlog.contextvars.bind_contextvars(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name
    )
    
    # 1. Validate time range
    try:
        time_range = await validate_time_range(event)
    except ManualCostUpdateError as e:
        return {
            "status_code": 400,
            "body": {"message": str(e)}
        }

    # 2. Invoke cost update
    try:
        await invoke_cost_update(time_range.start_time, time_range.end_time)
        return {
            "status_code": 200,
            "body": {"message": "Successfully invoked cost_update"}
        }
    except ManualCostUpdateError as e:
        return {
            "status_code": 500,
            "body": {"message": str(e)}
        }



