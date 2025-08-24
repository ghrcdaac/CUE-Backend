# --- src/python/event_lambdas/infected_logger/logic.py ---
import json
import logging
import boto3
import asyncio
import socket # Import the socket library for network testing
import os

from uuid import UUID
from asyncpg.pool import Pool
from .db import upsert_scan_status_in_database, get_collection_id
from .model import ScanResultMessage

logger = logging.getLogger(__name__)
eventbridge_client = boto3.client('events')
sqs_client = boto3.client('sqs')

STATUS_MAP = {
    "Clean": "clean",
    "Infected": "infected"
}
DEFAULT_STATUS = "scan_failed"
QUEUE_URL = os.environ.get("QUEUE_URL")


async def perform_network_diagnostics():
    """
    Performs basic network tests to check connectivity to the EventBridge endpoint.
    Returns True if all tests pass, False otherwise.
    """
    hostname = "events.us-west-2.amazonaws.com"
    port = 443
    logger.info(f"--- Starting Network Diagnostics for {hostname} ---")

    # Test 1: DNS Resolution
    try:
        ip_address = socket.gethostbyname(hostname)
        logger.info(f"DNS Test PASSED. '{hostname}' resolved to '{ip_address}'.")
    except socket.gaierror as e:
        logger.error(f"DNS Test FAILED. Could not resolve hostname '{hostname}'. Error: {e}", exc_info=True)
        return False

    # Test 2: TCP Socket Connection
    try:
        with socket.create_connection((hostname, port), timeout=10) as sock:
            logger.info(f"TCP Connection Test PASSED. Successfully connected to {hostname} on port {port}.")
    except (socket.timeout, OSError) as e:
        logger.error(f"TCP Connection Test FAILED. Could not connect to {hostname} on port {port}. Error: {e}", exc_info=True)
        return False
    
    logger.info("--- Network Diagnostics Passed ---")
    return True


async def publish_infected_file_event(scan_details: ScanResultMessage):
    """Publishes an event to EventBridge for an infected file."""
    # Run diagnostics before attempting to publish
    if not await perform_network_diagnostics():
        logger.error("Skipping EventBridge publish due to failed network diagnostics.")
        return # Do not attempt to publish if connectivity is broken

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
        logger.info(f"Successfully published event for key: {scan_details.key}")
    except Exception as e:
        logger.error(f"Failed to publish event to EventBridge for key {scan_details.key}: {e}", exc_info=True)

async def send_clean_file_message(file_id:UUID, collection_id:UUID) -> None:
    """Send a message to the clean file SQS queue for a file"""
    try:
        response = sqs_client.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=f'{{"file_id":"{file_id}", "collection_id":"{collection_id}"}}'
        )
        message_id = response.get("MessageId")
        logger.info(f"MessageId {message_id} for file {file_id}")
    except Exception as e:
        logger.error(f"Failed to publish event to SQS queue for {file_id}: {e}")
        raise


async def process_scan_result(message: ScanResultMessage, db_pool: Pool) -> None:
    """
    Processes a validated scan result message, upserts its status, and publishes an event if infected.
    """
    file_id = message.key
    status = STATUS_MAP.get(message.result, DEFAULT_STATUS)

    if status == DEFAULT_STATUS:
        logger.warning(f"Received unknown scan result '{message.result}' for file key {file_id}. Defaulting to '{DEFAULT_STATUS}'.")

    scan_details_dict = json.loads(message.model_dump_json(by_alias=True))
    update_data = {
        "status": status,
        "scan_start": message.date_scanned,
        "scan_end": message.date_scanned,
        "scan_results": json.dumps(scan_details_dict.get("scanResults"))
    }
    
    logger.info(f"Upserting file status for ID {file_id} with status '{status}'.")
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await upsert_scan_status_in_database(conn, file_id, update_data)
            if status == 'clean':
                collection_id = await get_collection_id(conn, file_id)
                if collection_id:
                    await send_clean_file_message(file_id, collection_id)
        
        # Only attempt to publish the event if the file was infected
        if status == 'infected':
            await publish_infected_file_event(message)

    except Exception as e:
        logger.error(f"Failed to run database transaction for file {file_id}: {e}", exc_info=True)
        raise
