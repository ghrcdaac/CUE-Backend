import asyncio
import json
import structlog
from typing import Any, Dict, Optional

from core.logging_config import setup_logging
from .model import parse_and_validate_message
from .logic import process_scan_result
from core.db_pool import get_database_pool

setup_logging()
logger = structlog.get_logger(__name__)


try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)


def parse_sqs_record(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        message_body_str = record.get('body')
        if not message_body_str:
            logger.error("sqs.record.body.missing")
            return None
        logger.info("sqs.record.body.received", body_content=message_body_str)
        return json.loads(message_body_str)
    except json.JSONDecodeError:
        logger.warning("sqs.record.body.invalid_json", body=message_body_str)
        return None
    except Exception:
        logger.error("sqs.record.parse_failed", exc_info=True)
        return None

async def async_handler(event: Dict[str, Any], context: object):
    structlog.contextvars.bind_contextvars(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name
    )
    logger.info("lambda.event.received", event_payload=event)
    pool = await get_database_pool()
    if not pool:
        logger.critical("db.pool.not_available.failing_invocation")
        raise RuntimeError("Database connection pool could not be initialized.")
    
    raw_messages = [msg for msg in (parse_sqs_record(rec) for rec in event.get('Records', [])) if msg is not None]
    validated_messages = [val_msg for val_msg in (parse_and_validate_message(raw_msg) for raw_msg in raw_messages) if val_msg is not None]
    
    if not validated_messages:
        logger.warning("sqs.batch.no_valid_messages")
        return
        
    logger.info("sqs.batch.processing", message_count=len(validated_messages))
    tasks = [process_scan_result(msg, pool) for msg in validated_messages]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    failed_tasks = [res for res in results if isinstance(res, Exception)]
    if failed_tasks:
        logger.error("sqs.batch.task_failed", error_count=len(failed_tasks), first_error=str(failed_tasks[0]))
        raise failed_tasks[0]
        
    logger.info("sqs.batch.success")

def handler(event: Dict[str, Any], context: object):
    """Synchronous entry point for AWS Lambda."""
    try:
        logger.info("infected.logger.event", message_count=len(event.get('Records', [])))
        loop.run_until_complete(async_handler(event, context))
    except Exception:
        logger.critical("lambda.handler.unhandled_exception", exc_info=True)
        raise
