import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional

from asyncpg.pool import Pool

from lambda_utils.database_util.db_util import get_connection_pool
from .db import RecordNotFoundError # Import our custom exception
from .logic import process_scan_result
from .model import parse_and_validate_message

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.getLogger().setLevel(log_level)


def parse_sqs_record(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Safely extracts the original SNS message from the SQS record's body."""
    try:
        message_body_str = record.get('body')
        if not message_body_str:
            logger.error("SQS record is missing 'body' field.")
            return None
        return json.loads(message_body_str)
    except json.JSONDecodeError:
        # This is expected for the non-JSON health messages. Log as warning.
        logger.warning(f"Message body is not valid JSON, likely a health check. Body: '{message_body_str}'")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during SQS record parsing: {e}", exc_info=True)
        return None


async def async_handler(event: Dict[str, Any], context: object) -> Dict[str, Any]:
    """Asynchronous main handler logic."""
    pool = None
    try:
        logger.info("Initializing database connection pool for this invocation.")
        pool = await get_connection_pool()
        logger.info("Database connection pool initialized successfully.")
        
        raw_messages = [msg for msg in (parse_sqs_record(rec) for rec in event.get('Records', [])) if msg is not None]
        validated_messages = [val_msg for val_msg in (parse_and_validate_message(raw_msg) for raw_msg in raw_messages) if val_msg is not None]

        if not validated_messages:
            logger.warning("No valid messages found after SQS parsing and validation.")
            return {"statusCode": 200, "body": "No valid messages to process."}

        logger.info(f"Processing {len(validated_messages)} validated message(s).")
        tasks = [process_scan_result(msg, pool) for msg in validated_messages]
        
        # MODIFIED: We now check the results of our tasks.
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check if any of the tasks failed.
        failed_tasks = [res for res in results if isinstance(res, Exception)]
        if failed_tasks:
            # If any task failed (e.g., with our RecordNotFoundError),
            # we raise the first exception. This tells SQS to retry the whole batch.
            logger.error(f"{len(failed_tasks)} task(s) failed. Raising exception to trigger SQS retry.")
            raise failed_tasks[0]

    except RecordNotFoundError as e:
        # Specifically catch our custom error to log it clearly and re-raise.
        logger.error(f"Race condition detected: {e}. Raising error to trigger SQS retry.")
        raise
    except Exception as e:
        logger.critical(f"A critical error occurred in the handler, will trigger retry: {e}", exc_info=True)
        # Re-raising the exception is crucial for SQS retries.
        raise
    finally:
        if pool:
            logger.info("Closing database connection pool.")
            await pool.close()

    logger.info("Finished processing event successfully.")
    return {"statusCode": 200, "body": "Successfully processed event batch."}



def handler(event: Dict[str, Any], context: object) -> Dict[str, Any]:
    """Synchronous entry point for AWS Lambda."""
    logger.info(f"Received event from SQS record(s): {event} ")
    logger.info(f"Received event with {len(event.get('Records', []))} SQS record(s).")
    return asyncio.run(async_handler(event, context))
