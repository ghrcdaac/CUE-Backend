# ./src/python/event_lambdas/notification_manager/handler.py
import asyncio
import json
import logging
import os
import boto3
from pathlib import Path

from lambda_utils.database_util.db_util import get_connection_pool
# Updated to use the new, more comprehensive DB function
from .db import get_notification_details_for_file

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

lambda_client = boto3.client('lambda')

def load_template(file_id, scan_details, notification_details):
    """Loads and populates the HTML email template with all necessary details."""
    try:
        template_path = Path(__file__).parent / "templates" / "infected_file_template.html"
        with open(template_path, 'r') as f:
            html_content = f.read()

        # Populate with data from the notification_details dictionary
        html_content = html_content.replace("{{ file_name }}", notification_details.get("file_name", "N/A"))
        html_content = html_content.replace("{{ uploader_name }}", notification_details.get("uploader_name", "N/A"))
        html_content = html_content.replace("{{ collection_name }}", notification_details.get("collection_name", "N/A"))

        # Populate with data from the original scan event
        html_content = html_content.replace("{{ file_id }}", str(file_id))
        html_content = html_content.replace("{{ scan_result }}", scan_details.get("result", "N/A"))
        html_content = html_content.replace("{{ date_scanned }}", scan_details.get("dateScanned", "N/A"))
        virus_names = ", ".join(scan_details.get("scanResults", [{}])[0].get("virusName", ["None"]))
        html_content = html_content.replace("{{ virus_names }}", virus_names)

        return html_content
    except Exception as e:
        logger.error(f"Failed to load or format email template: {e}", exc_info=True)
        return "Error: Could not generate email body."


async def process_event(event):
    """Main logic for a single event."""
    scan_details = event['detail']
    file_id = scan_details['key']
    
    logger.info(f"Processing infected file notification for key: {file_id}")

    pool = await get_connection_pool()
    notification_details = None
    try:
        async with pool.acquire() as conn:
            # Call the new DB function to get all details at once
            notification_details = await get_notification_details_for_file(conn, file_id)
    finally:
        await pool.close()

    if not notification_details:
        logger.warning(f"Could not retrieve notification details or recipients for file {file_id}. No email will be sent.")
        return

    recipients = notification_details.get('recipient_emails', [])
    if not recipients:
        logger.warning(f"Recipient list is empty for file {file_id}. No email will be sent.")
        return

    # Prepare email content
    subject = f"CUE Security Alert: Infected File Detected - {notification_details.get('file_name', file_id)}"
    body_html = load_template(file_id, scan_details, notification_details)
    body_text = (
        f"An infected file was detected in the CUE system.\n"
        f"File Name: {notification_details.get('file_name', 'N/A')}\n"
        f"Uploaded By: {notification_details.get('uploader_name', 'N/A')}\n"
        f"Collection: {notification_details.get('collection_name', 'N/A')}\n"
        f"File ID: {file_id}\n\n"
        "Please see the HTML version of this email for full details."
    )

    # Prepare payload for the email sender lambda
    payload = {
        "recipients": recipients,
        "subject": subject,
        "body_html": body_html,
        "body_text": body_text
    }

    # Invoke the email sender lambda asynchronously
    try:
        logger.info(f"Invoking email sender lambda for {len(recipients)} recipient(s).")
        lambda_client.invoke(
            FunctionName=os.environ['EMAIL_SENDER_ARN'],
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
    except Exception as e:
        logger.error(f"Failed to invoke email-sender lambda: {e}", exc_info=True)


async def async_handler(event, context):
    """Async handler to process one or more events."""
    await process_event(event)

def handler(event, context):
    """Synchronous entrypoint for AWS Lambda."""
    logger.info(f"Received event: {json.dumps(event)}")
    return asyncio.run(async_handler(event, context))
