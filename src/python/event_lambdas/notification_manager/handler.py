import asyncio
import json
import logging
import os
import boto3
from pathlib import Path

from lambda_utils.database_util.db_util import get_connection_pool
from .db import get_daac_manager_emails_for_file

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

lambda_client = boto3.client('lambda')

def load_template(file_id, scan_details):
    """Loads and populates the HTML email template."""
    try:
        # Construct path to template file within the package
        template_path = Path(__file__).parent / "templates" / "infected_file_template.html"
        with open(template_path, 'r') as f:
            html_content = f.read()

        # Simple replacement for template placeholders
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
    try:
        async with pool.acquire() as conn:
            recipients = await get_daac_manager_emails_for_file(conn, file_id)
    finally:
        await pool.close()

    if not recipients:
        logger.warning(f"No DAAC Manager recipients found for file {file_id}. No email will be sent.")
        return

    # Prepare email content
    subject = f"CUE Security Alert: Infected File Detected - {file_id}"
    body_html = load_template(file_id, scan_details)
    body_text = f"An infected file was detected in the CUE system. File ID: {file_id}. Please see the HTML version for details."

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
            InvocationType='Event', # Fire and forget
            Payload=json.dumps(payload)
        )
    except Exception as e:
        logger.error(f"Failed to invoke email-sender lambda: {e}", exc_info=True)


async def async_handler(event, context):
    """Async handler to process one or more events."""
    # EventBridge sends a single event, not a list of records.
    await process_event(event)

def handler(event, context):
    """Synchronous entrypoint for AWS Lambda."""
    logger.info(f"Received event: {json.dumps(event)}")
    return asyncio.run(async_handler(event, context))