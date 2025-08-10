# ./src/python/event_lambdas/notification_manager/handler.py
import asyncio
import json
import logging
import os
import boto3
from pathlib import Path

from lambda_utils.database_util.db_util import get_connection_pool
# Updated to use the new, more comprehensive DB function
from .db import get_infected_file_details
from .logic import process_notification

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

lambda_client = boto3.client('lambda')

def load_template(template_name: str, context: dict) -> str:
    """Loads and populates an HTML email template."""
    try:
        template_path =  Path(__file__).parent / "templates" / template_name
        with open(template_path, 'r') as f:
            html_content = f.read()
        for key, value in context.items():
            html_content = html_content.replace(f"{{{{ {key} }}}}", str(value))
        return html_content
    except Exception as e:
        #logger.error(f"template.load.failed", template=template_name, exc_info=True)
        return "Error: Could not generate email body."


async def async_handler(event, context):
    """Async handler to process one or more events."""
    detail_type = event.get('detail-type')
    detail = event.get('detail', {})

    if detail_type == "ScheduledInfectedFileNotification":
        await handle_infected_files(detail)
    else:
        logger.warning("event.unhandled_type")

def handler(event, context):
    """Synchronous entrypoint for AWS Lambda."""
    logger.info(f"Received event: {json.dumps(event)}")
    return asyncio.run(async_handler(event, context))

async def handle_infected_files(detail):
    logger.info(f"event.scheduled_infected_files_notif.send {detail}")
    pool = await get_connection_pool()
    notification_details = None
    hours = 1
    try:
        async with pool.acquire() as conn:
            notification_details = await get_infected_file_details(conn, hours)
            if not notification_details:
                logger.info("No infected file notifications to send")
                return None
    finally:
        await pool.close()

    for ngroup_id, details in notification_details.items():
        logger.info(f"processing notification for ngroup: {ngroup_id}")
        subject, html_details, body_text = await process_notification(details)
        body_html = load_template("infected_files_template.html", html_details)
        await invoke_email_sender(details['recipient_emails'], subject, body_html, body_text)

async def invoke_email_sender(recipients: list, subject: str, body_html: str, body_text: str):
    """Prepares payload and invokes the email_sender Lambda."""
    payload = {"recipients": recipients, "subject": subject, "body_html": body_html, "body_text": body_text}
    try:
        #logger.info("email_sender.invoke.started", recipient_count=len(recipients))
        lambda_client.invoke(
            FunctionName=os.environ['EMAIL_SENDER_ARN'],
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
    except Exception as e:
        logger.error("email_sender.invoke.failed", exc_info=True)
