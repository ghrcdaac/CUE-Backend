import json
import logging
import boto3

from asyncpg.pool import Pool
from .db import update_scan_status_in_database
from .model import ScanResultMessage

logger = logging.getLogger(__name__)
eventbridge_client = boto3.client('events')

STATUS_MAP = {
    "Clean": "clean",
    "Infected": "infected"
}
DEFAULT_STATUS = "scan_failed"

async def publish_infected_file_event(scan_details: ScanResultMessage):
    """Publishes an event to EventBridge for an infected file."""
    logger.info(f"Publishing 'InfectedFileFound' event for key: {scan_details.key}")
    try:
        eventbridge_client.put_events(
            Entries=[
                {
                    'Source': 'com.cue.scanner',
                    'DetailType': 'InfectedFileFound',
                    'Detail': scan_details.model_dump_json(by_alias=True),
                    'EventBusName': 'cue-application-bus'
                }
            ]
        )
    except Exception as e:
        logger.error(f"Failed to publish event to EventBridge for key {scan_details.key}: {e}", exc_info=True)


async def process_scan_result(message: ScanResultMessage, db_pool: Pool) -> None:
    """
    Processes a validated scan result message, transforms data, and updates the database.
    If the file is infected, it publishes an event.
    """
    file_id = message.key
    status = STATUS_MAP.get(message.result, DEFAULT_STATUS)

    if status == DEFAULT_STATUS:
        logger.warning(f"Received unknown scan result '{message.result}' for file key {file_id}. Defaulting to '{DEFAULT_STATUS}'.")

    # Prepare data for DB update
    scan_details_dict = json.loads(message.model_dump_json(by_alias=True))
    update_data = {
        "status": status,
        "scan_start": message.date_scanned,
        "scan_end": message.date_scanned,
        "scan_results": json.dumps(scan_details_dict.get("scanResults"))
    }
    
    logger.info(f"Updating file status for ID {file_id} with status '{status}'.")
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await update_scan_status_in_database(conn, file_id, update_data)
        
        # --- NEW: Publish event if infected ---
        if status == 'infected':
            await publish_infected_file_event(message)

    except Exception as e:
        logger.error(f"Failed to run database transaction for file {file_id}: {e}", exc_info=True)
        raise
