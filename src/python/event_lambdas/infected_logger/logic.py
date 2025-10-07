import json
import boto3
import asyncio
import os
import structlog
import asyncpg
from uuid import UUID, uuid4

from db import process_scan_result_in_database
from model import ScanResultMessage, ScanResultDetailJSONEncoder

logger = structlog.get_logger(__name__)

# Initialize boto3 clients once per container
lambda_client = boto3.client('lambda')
sqs_client = boto3.client('sqs')
eventbridge_client = boto3.client('events')

# --- Environment Variable Configuration ---
# The new feature flag to toggle between invocation modes ('SQS' or 'LAMBDA')
TRANSFER_INVOCATION_MODE = os.environ.get("TRANSFER_INVOCATION_MODE", "SQS").upper()
# The ARN or name of the file_transfer lambda
FILE_TRANSFER_LAMBDA_NAME = os.environ.get("FILE_TRANSFER_LAMBDA_NAME")
# The URL for the existing clean files SQS queue
CLEAN_FILES_QUEUE_URL = os.environ.get("QUEUE_URL")

STATUS_MAP = {"Clean": "clean", "Infected": "infected"}
DEFAULT_STATUS = "scan_failed"


async def publish_infected_file_event(scan_details: ScanResultMessage):
    """Publishes an event to EventBridge for an infected file."""
    logger.info("eventbridge.publish.started", file_id=str(scan_details.key))
    try:
        await asyncio.to_thread(
            eventbridge_client.put_events,
            Entries=[{
                'Source': 'com.cue.scanner',
                'DetailType': 'InfectedFileFound',
                'Detail': scan_details.model_dump_json(by_alias=True),
                'EventBusName': 'cue-application-bus'
            }]
        )
        logger.info("eventbridge.publish.success", file_id=str(scan_details.key))
    except Exception:
        logger.error("eventbridge.publish.failed", file_id=str(scan_details.key), exc_info=True)
        # We don't re-raise, as the primary DB update has succeeded. Monitoring should catch this.

async def send_clean_file_message_sqs(file_id: UUID, collection_id: UUID):
    """Sends a message to the clean file SQS queue."""
    if not CLEAN_FILES_QUEUE_URL:
        logger.error("sqs.send.failed.no_queue_url_configured")
        return

    logger.info("sqs.send.started", file_id=str(file_id), queue_url=CLEAN_FILES_QUEUE_URL)
    try:
        await asyncio.to_thread(
            sqs_client.send_message,
            QueueUrl=CLEAN_FILES_QUEUE_URL,
            MessageBody=json.dumps({"file_id": str(file_id), "collection_id": str(collection_id)})
        )
        logger.info("sqs.send.success", file_id=str(file_id))
    except Exception:
        logger.error("sqs.send.failed", file_id=str(file_id), exc_info=True)
        raise

async def invoke_file_transfer_lambda(file_id: UUID, collection_id: UUID):
    """Asynchronously invokes the file_transfer lambda directly."""
    if not FILE_TRANSFER_LAMBDA_NAME:
        logger.error("lambda.invoke.failed.no_lambda_name_configured")
        return

    logger.info("lambda.invoke.started", file_id=str(file_id), lambda_name=FILE_TRANSFER_LAMBDA_NAME)
    
    # This payload mimics an SQS event so the file_transfer lambda
    # can use the exact same parsing logic for both invocation types.
    payload = {
        "Records": [{
            "messageId": str(uuid4()),
            "body": json.dumps({
                "file_id": str(file_id),
                "collection_id": str(collection_id)
            })
        }]
    }

    try:
        await asyncio.to_thread(
            lambda_client.invoke,
            FunctionName=FILE_TRANSFER_LAMBDA_NAME,
            InvocationType='Event',  # 'Event' makes the call asynchronous
            Payload=json.dumps(payload)
        )
        logger.info("lambda.invoke.success", file_id=str(file_id))
    except Exception:
        logger.error("lambda.invoke.failed", file_id=str(file_id), exc_info=True)
        raise

async def process_scan_result(message: ScanResultMessage, db_pool: asyncpg.Pool):
    """
    Processes a validated scan result, updates the database, and triggers the next
    step in the workflow using the configured invocation mode.
    """
    file_id = message.key
    status = STATUS_MAP.get(message.result, DEFAULT_STATUS)
    
    # --- Correctly prepare scan_results based on status ---
    if status == 'infected':
        # For infected files, serialize the ENTIRE message for a full audit trail.
        scan_results_json = message.model_dump_json(by_alias=True)
    else:
        # For other statuses, serialize only the 'scanResults' array.
        scan_results_list = message.model_dump(by_alias=True).get("scanResults")
        scan_results_json = json.dumps(scan_results_list, cls=ScanResultDetailJSONEncoder)

    update_data = {
        "status": status,
        "scan_start": message.date_scanned,
        "scan_end": message.date_scanned,
        "scan_results": scan_results_json
    }
    
    logger.info("scan_result.processing", file_id=str(file_id), status=status)
    
    async with db_pool.acquire() as conn:
        # Pass the pre-formatted data to the database function
        collection_id, final_status = await process_scan_result_in_database(conn, file_id, update_data)

    # --- Main Workflow Logic based on the confirmed status from the DB ---
    if final_status == 'clean' and collection_id:
        if TRANSFER_INVOCATION_MODE == "LAMBDA":
            await invoke_file_transfer_lambda(file_id, collection_id)
        else: # Default to SQS for safety
            await send_clean_file_message_sqs(file_id, collection_id)
            
    elif final_status == 'infected':
        await publish_infected_file_event(message)

    elif final_status == 'scan_failed':
        logger.warning("scan.failed", file_id=str(file_id), scan_result=message.result)

