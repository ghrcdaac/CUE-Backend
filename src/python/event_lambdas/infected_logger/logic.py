import json
import boto3
import asyncio
import os
import structlog
import asyncpg
from uuid import UUID, uuid4
from datetime import timedelta

from db import (
    process_scan_result_in_database,
    count_provider_infected_files,
    block_provider_instant
)
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
# Defaults to 5 files if not set
INFECTED_FILE_THRESHOLD = int(os.getenv("INFECTED_FILE_THRESHOLD", "5"))
# Defaults to 24 hours if not set
BLOCKING_LOOKBACK_HOURS = int(os.getenv("BLOCKING_LOOKBACK_HOURS", "24"))

# HDF Vulnerability Scanner configuration
ENABLE_HDF5_SCANNER = os.environ.get("ENABLE_HDF5_SCANNER", "false").lower() == "true"
HDF_VULNERABILITY_SCANNER_LAMBDA_NAME = os.environ.get("HDF_VULNERABILITY_SCANNER_LAMBDA_NAME")

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

async def invoke_hdf_vulnerability_scanner(file_id: UUID, collection_id: UUID):
    """Asynchronously invokes the hdf_vulnerability_scanner lambda."""
    if not HDF_VULNERABILITY_SCANNER_LAMBDA_NAME:
        logger.error("lambda.invoke.failed.no_hdf_scanner_lambda_name_configured")
        return

    logger.info("lambda.invoke.hdf_scanner.started", file_id=str(file_id), lambda_name=HDF_VULNERABILITY_SCANNER_LAMBDA_NAME)
    
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
            FunctionName=HDF_VULNERABILITY_SCANNER_LAMBDA_NAME,
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
        logger.info("lambda.invoke.hdf_scanner.success", file_id=str(file_id))
    except Exception:
        logger.error("lambda.invoke.hdf_scanner.failed", file_id=str(file_id), exc_info=True)
        raise

async def process_scan_result(message: ScanResultMessage, db_pool: asyncpg.Pool):
    """
    Processes a validated scan result, updates the database, triggers the next
    step, and performs instant provider blocking if the threshold is met.
    """
    file_id = message.key
    status = STATUS_MAP.get(message.result, DEFAULT_STATUS)
    
    if status == 'infected':
        scan_results_json = message.model_dump_json(by_alias=True)
    else:
        scan_results_list = message.model_dump(by_alias=True).get("scanResults")
        scan_results_json = json.dumps(scan_results_list, cls=ScanResultDetailJSONEncoder)

    update_data = {
        "status": status,
        "scan_start": message.date_scanned,
        "scan_end": message.date_scanned,
        "scan_results": scan_results_json
    }
    
    logger.info("scan_result.processing", file_id=str(file_id), status=status)
    
    collection_id = None
    final_status = "unknown"
    provider_id = None # Initialize provider_id
    filename = None
    
    async with db_pool.acquire() as conn:
       
        collection_id, final_status, provider_id, filename = await process_scan_result_in_database(conn, file_id, update_data)

      
        if final_status == 'infected' and provider_id:
            logger.info("infected_file.provider_check", file_id=str(file_id), provider_id=str(provider_id))
            lookback_window = timedelta(hours=BLOCKING_LOOKBACK_HOURS)
            infected_count = await count_provider_infected_files(conn, provider_id, lookback_window)

            if infected_count >= INFECTED_FILE_THRESHOLD:
                logger.warning("provider.threshold_exceeded.blocking",
                               provider_id=str(provider_id),
                               infected_count=infected_count,
                               threshold=INFECTED_FILE_THRESHOLD,
                               lookback_hours=BLOCKING_LOOKBACK_HOURS)
                reason = f"Provider automatically blocked after uploading {infected_count} infected files within {BLOCKING_LOOKBACK_HOURS} hour(s) (Threshold: {INFECTED_FILE_THRESHOLD})."
                await block_provider_instant(conn, provider_id, reason)
            else:
                 logger.info("provider.threshold_not_met",
                               provider_id=str(provider_id),
                               infected_count=infected_count,
                               threshold=INFECTED_FILE_THRESHOLD)

  
    if final_status == 'clean' and collection_id:
        is_hdf5 = filename and (filename.lower().endswith('.h5') or filename.lower().endswith('.hdf5') or filename.lower().endswith('.he5'))
        is_zip = filename and filename.lower().endswith('.zip')
        
        if ENABLE_HDF5_SCANNER and (is_hdf5 or is_zip):
            logger.info("hdf_scanner.intercept", file_id=str(file_id), filename=filename)
            await invoke_hdf_vulnerability_scanner(file_id, collection_id)
        else:
            if TRANSFER_INVOCATION_MODE == "LAMBDA":
                await invoke_file_transfer_lambda(file_id, collection_id)
            else: # Default to SQS for safety
                await send_clean_file_message_sqs(file_id, collection_id)
            
    # elif final_status == 'infected':
    #     await publish_infected_file_event(message)

    elif final_status == 'scan_failed':
        logger.warning("scan.failed", file_id=str(file_id), scan_result=message.result)

