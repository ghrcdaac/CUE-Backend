# --- src/python/event_lambdas/infected_logger/logic.py ---
import json
import boto3
import asyncio
import socket # Import the socket library for network testing
import os
import structlog

from core.db import get_db_connection
from db import upsert_scan_status_in_database, get_collection_id
from model import ScanResultMessage, ScanResultDetailJSONEncoder
from uuid import UUID

logger = structlog.get_logger(__name__)
eventbridge_client = boto3.client('events')
sqs_client = boto3.client('sqs')

STATUS_MAP = {"Clean": "clean", "Infected": "infected"}
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
    logger.info("eventbridge.publish.started", file_id=str(scan_details.key))
    try:
        eventbridge_client.put_events(
            Entries=[{
                'Source': 'com.cue.scanner',
                'DetailType': 'InfectedFileFound',
                'Detail': scan_details.model_dump_json(by_alias=True),
                'EventBusName': 'cue-application-bus'
            }]
        )
        logger.info("eventbridge.publish.success", file_id=str(scan_details.key))
    except Exception as e:
        logger.error("eventbridge.publish.failed", file_id=str(scan_details.key), exc_info=True)
        # We don't re-raise here, because the DB update has already succeeded.
        # A monitoring system should alert on these logs.

async def send_clean_file_message(file_id:UUID, collection_id:UUID):
    """Send a message to the clean file SQS queue"""
    try:
        response = sqs_client.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=f'{{"file_id":"{file_id}", "collection_id":"{collection_id}"}}'
        )
        message_id = response.get("MessageId")
        logger.info("sqs.clean_queue.send_message.success", file_id=str(file_id), collection_id=str(collection_id), message_id=message_id)
    except Exception as e:
        logger.info("sqs.clean_queue.send_message.failed", file_id=str(file_id), collection_id=str(collection_id))
        raise

async def process_scan_result(message: ScanResultMessage):
    """
    Processes a validated scan result message, upserts its status,
    and publishes an event if infected.
    """
    file_id = message.key
    status = STATUS_MAP.get(message.result, DEFAULT_STATUS)
    scan_results = json.dumps(
        message.model_dump(by_alias=True).get("scanResults"),
        cls=ScanResultDetailJSONEncoder
    )

    update_data = {
        "status": status,
        "scan_start": message.date_scanned,
        "scan_end": message.date_scanned,
        "scan_results": scan_results
    }
    
    logger.info("scan_result.processing", file_id=str(file_id), status=status)
    
    async with get_db_connection() as conn:
        await upsert_scan_status_in_database(conn, file_id, update_data)
    
        if status == 'clean':
            collection_id = await get_collection_id(conn, file_id)
            await send_clean_file_message(file_id, collection_id)

    if status == 'infected':
        await publish_infected_file_event(message)