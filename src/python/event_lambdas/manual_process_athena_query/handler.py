import asyncio
import structlog
import boto3
from logic import invoke_process_athena_query, validate_athena_query_details, ManualProcessAthenaQueryError

from core.logging_config import setup_logging

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

    # 1. Validate Athena query 
    try: 
        athena_details = await validate_athena_query_details(event)
    except ManualProcessAthenaQueryError as e:
        return {
            "status_code": 400,
            "body":{"message": str(e)}
        }

    # 2. Invoke process_athena_query 
    try:
        await invoke_process_athena_query(athena_details.current_state, athena_details.query_id)
        return {
            "status_code": 200,
            "body": {"message": "Successfully invoked process_athena_query"}
        }
    except ManualProcessAthenaQueryError as e: 
        return {
            "status_code": 500,
            "body": {"message": str(e)}
        }



