# --- src/python/event_lambdas/infected_logger/handler.py ---
import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional

# --- Aggressive Logging Configuration for Debugging ---
# We configure the root logger immediately to catch any possible error.
try:
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    # Using force=True ensures the logger is reconfigured even in a warm container.
    logging.basicConfig(level=log_level, format='%(levelname)s:[%(name)s]:%(message)s', force=True)
    logger = logging.getLogger(__name__)
    logger.info("Initial logging configured successfully.")
except Exception as e:
    # This is a last resort if basic logging setup fails.
    print(f"CRITICAL: Failed to configure logger: {e}")

# --- Defensive Imports ---
# We will now import modules one by one inside a try block to find the source of the crash.
try:
    from asyncpg.pool import Pool
    from asyncpg.exceptions import ForeignKeyViolationError
    from lambda_utils.database_util.db_util import get_connection_pool
    logger.info("Successfully imported standard libraries and asyncpg.")

    from .model import parse_and_validate_message
    logger.info("Successfully imported 'model' module.")

    from .logic import process_scan_result
    logger.info("Successfully imported 'logic' module.")

except ImportError as e:
    logger.critical(f"CRITICAL IMPORT ERROR: Failed to import a required module. This is likely the cause of the silent failure. Error: {e}", exc_info=True)
    # Raising here will ensure the Lambda exits with a clear error if an import fails.
    raise
except Exception as e:
    logger.critical(f"An unexpected error occurred during the import phase: {e}", exc_info=True)
    raise

logger.info("Lambda container successfully initialized with all modules.")


def parse_sqs_record(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Safely extracts the original SNS message from the SQS record's body."""
    try:
        message_body_str = record.get('body')
        if not message_body_str:
            logger.error("SQS record is missing 'body' field.")
            return None
        return json.loads(message_body_str)
    except json.JSONDecodeError:
        logger.warning(f"Message body is not valid JSON, likely a health check. Body: '{message_body_str}'")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during SQS record parsing: {e}", exc_info=True)
        return None


async def async_handler(event: Dict[str, Any], context: object):
    """Async handler to process one or more events."""
    logger.info("Async handler started. Processing event.")
    pool = None
    try:
        logger.info("Initializing database connection pool for this invocation.")
        pool = await get_connection_pool()
        logger.info("Database connection pool initialized successfully.")
        
        raw_messages = [msg for msg in (parse_sqs_record(rec) for rec in event.get('Records', [])) if msg is not None]
        validated_messages = [val_msg for val_msg in (parse_and_validate_message(raw_msg) for raw_msg in raw_messages) if val_msg is not None]

        if not validated_messages:
            logger.warning("No valid messages found after SQS parsing and validation.")
            return

        logger.info(f"Processing {len(validated_messages)} validated message(s).")
        tasks = [process_scan_result(msg, pool) for msg in validated_messages]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        failed_tasks = [res for res in results if isinstance(res, Exception)]
        if failed_tasks:
            logger.error(f"{len(failed_tasks)} task(s) failed. Raising exception to trigger SQS retry.")
            raise failed_tasks[0]

    except ForeignKeyViolationError as e:
        logger.error(f"Race condition detected: {e}. Raising error to trigger SQS retry.")
        raise
    except Exception as e:
        logger.critical(f"A critical error occurred in the handler, will trigger retry: {e}", exc_info=True)
        raise
    finally:
        if pool:
            logger.info("Closing database connection pool.")
            await pool.close()

    logger.info("Finished processing event successfully.")


def handler(event: Dict[str, Any], context: object) -> Dict[str, Any]:
    """Synchronous entry point for AWS Lambda."""
    logger.info(f"Received event from SQS record(s): {event} ")
    logger.info(f"Received event with {len(event.get('Records', []))} SQS record(s).")
    try:
        asyncio.run(async_handler(event, context))
    except Exception as e:
        logger.critical(f"FATAL: Unhandled exception in top-level handler: {e}", exc_info=True)
        # Re-raising is important for Lambda to know the invocation failed.
        raise
