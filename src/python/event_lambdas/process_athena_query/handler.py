import asyncio
import structlog
import json

from .model import parse_and_validate_event_detail
from .logic import (
    get_query_results_as_json, 
    get_query_error_reason, 
    store_result_in_s3,
    QueryProcessingError
)
from core.logging_config import setup_logging

# Initialize logging
setup_logging()
logger = structlog.get_logger(__name__)

try:
    loop = asyncio.get_running_loop()
except RuntimeError: 
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

def handler(event, context):
    """
    Lambda handler triggered by EventBridge for Athena query state changes.
    Processes succeeded or failed queries and stores the result as a JSON file in S3.
    """
    try:
        loop.run_until_complete(async_handler(event, context))
    except Exception:
        logger.critical("lambda.handler.unhandled_exception", exc_info=True)
        raise
    
async def async_handler(event, context):
    structlog.contextvars.bind_contextvars(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name
    )

    logger.info("event.received", full_event=event)

    detail = event.get('detail')
    if not detail:
        logger.warning("event.detail.missing")
        return

    validated_detail = parse_and_validate_event_detail(detail)
    if not validated_detail:
        # The model validation function already logged the error
        return

    query_exec_id = validated_detail.query_execution_id
    query_state = validated_detail.current_state
    result_key = f"{query_exec_id}.json"

    logger.info("athena.query.processing", query_id=query_exec_id, state=query_state)

    try:
        if query_state == "SUCCEEDED":
            results_json = await get_query_results_as_json(query_exec_id)
            await store_result_in_s3(results_json, result_key)
            logger.info("athena.query.succeeded", query_id=query_exec_id)

        elif query_state == "FAILED":
            error_reason = await get_query_error_reason(query_exec_id)
            error_json = json.dumps({"detail": "Failed", "message": error_reason})
            await store_result_in_s3(error_json, result_key)
            logger.warning("athena.query.failed", query_id=query_exec_id, reason=error_reason)

        else:
            logger.info("athena.query.state.ignored", query_id=query_exec_id, state=query_state)

    except (QueryProcessingError, Exception) as e:
        # If any part of the logic fails, log the critical error.
        # This will cause the Lambda to fail, allowing for potential retries via a DLQ.
        logger.critical("lambda.handler.unhandled_exception", query_id=query_exec_id, exc_info=True)
        raise
