import asyncio
import json
import structlog
from typing import Any, Dict, Optional

# Import v2 standard modules
from core.logging_config import setup_logging
from model import parse_and_validate_message
from logic import process_scan_result

# Initialize logging at the start of the module
setup_logging()
logger = structlog.get_logger(__name__)

def parse_sqs_record(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Safely extracts the original SNS message from the SQS record's body."""
    try:
        message_body_str = record.get('body')
        if not message_body_str:
            logger.error("sqs.record.body.missing")
            return None
        return json.loads(message_body_str)
    except json.JSONDecodeError:
        logger.warning("sqs.record.body.invalid_json", body=message_body_str)
        return None
    except Exception as e:
        logger.error("sqs.record.parse_failed", exc_info=True)
        return None

async def async_handler(event: Dict[str, Any], context: object):
    """Async handler to process one or more SQS records."""
    structlog.contextvars.bind_contextvars(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name
    )

    raw_messages = [msg for msg in (parse_sqs_record(rec) for rec in event.get('Records', [])) if msg is not None]
    validated_messages = [val_msg for val_msg in (parse_and_validate_message(raw_msg) for raw_msg in raw_messages) if val_msg is not None]

    if not validated_messages:
        logger.warning("sqs.batch.no_valid_messages")
        return

    logger.info("sqs.batch.processing", message_count=len(validated_messages))
    tasks = [process_scan_result(msg) for msg in validated_messages]
    
    # asyncio.gather will run all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    failed_tasks = [res for res in results if isinstance(res, Exception)]
    if failed_tasks:
        logger.error("sqs.batch.task_failed", error_count=len(failed_tasks), first_error=str(failed_tasks[0]))
        # Re-raise the first exception to signal failure to SQS, triggering a retry for the whole batch.
        raise failed_tasks[0]

    logger.info("sqs.batch.success")

def handler(event: Dict[str, Any], context: object):
    """Synchronous entry point for AWS Lambda."""
    try:
        logger.info("infected.logger.event", message_count=len(event))
        logger.info(event)
        asyncio.run(async_handler(event, context))
    except Exception as e:
        logger.critical("lambda.handler.unhandled_exception", exc_info=True)
        # Re-raising is important for Lambda to know the invocation failed. . check
        raise
