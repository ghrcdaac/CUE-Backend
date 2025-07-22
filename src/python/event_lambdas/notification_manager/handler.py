# ==============================================================================
# File: src/python/event_lambdas/notification_manager/handler.py (Refactored)
# Purpose: This Lambda now acts as a central dispatcher for multiple event types,
# using the modern, consistent architecture.
# ==============================================================================
import asyncio
import json
import os
import boto3
import structlog # Use structlog
from pathlib import Path
from uuid import UUID

# Import the new logging setup and DB connection method
from logging_config import setup_logging
from core.db import get_db_connection
from .db import (
    get_infected_file_details, 
    get_new_application_details, 
    get_approved_user_details
)

# Initialize logging at the start of the module
setup_logging()
logger = structlog.get_logger(__name__)

lambda_client = boto3.client('lambda')

def load_template(template_name: str, context: dict) -> str:
    """Loads and populates an HTML email template."""
    try:
        template_path = Path(__file__).parent / "templates" / template_name
        with open(template_path, 'r') as f:
            html_content = f.read()
        for key, value in context.items():
            html_content = html_content.replace(f"{{{{ {key} }}}}", str(value))
        return html_content
    except Exception as e:
        logger.error(f"template.load.failed", template=template_name, exc_info=True)
        return "Error: Could not generate email body."

async def handle_infected_file(detail: dict):
    """Handles logic for the original infected file notification."""
    file_id = detail['key']
    logger.info("event.infected_file.received", file_id=file_id)
    
    # Use the new connection-per-task pattern
    async with get_db_connection() as conn:
        details = await get_infected_file_details(conn, file_id)

    if not details or not details.get('recipient_emails'):
        logger.warning("notification.recipients.not_found", alert_type="infected_file", file_id=file_id)
        return
    
    subject = f"CUE Security Alert: Infected File Detected - {details.get('file_name', file_id)}"
    body_html = load_template("infected_file_template.html", {**detail, **details})
    body_text = f"An infected file was detected: {details.get('file_name')}"
    await invoke_email_sender(details['recipient_emails'], subject, body_html, body_text)

async def handle_application_submitted(detail: dict):
    """Handles sending a notification to admins about a new application."""
    app_id = UUID(detail["application_id"])
    logger.info("event.application_submitted.received", application_id=str(app_id))
    
    async with get_db_connection() as conn:
        details = await get_new_application_details(conn, app_id)
        
    if not details or not details.get('recipient_emails'):
        logger.warning("notification.recipients.not_found", alert_type="application_submitted", application_id=str(app_id))
        return
        
    subject = f"New CUE User Application for {details.get('ngroup_name', 'N/A')}"
    body_html = load_template("new_application_admin_alert.html", details)
    body_text = f"A new user application from {details.get('user_name')} has been submitted."
    await invoke_email_sender(details['recipient_emails'], subject, body_html, body_text)

async def handle_application_approved(detail: dict):
    """Handles sending a welcome email to a newly approved user."""
    user_id = UUID(detail["user_id"])
    logger.info("event.application_approved.received", user_id=str(user_id))
    
    async with get_db_connection() as conn:
        details = await get_approved_user_details(conn, user_id)
        
    if not details:
        logger.warning("notification.user_details.not_found", alert_type="application_approved", user_id=str(user_id))
        return
        
    subject = "Welcome to the CUE System!"
    details["dashboard_url"] = os.getenv("FRONTEND_URL", "http://localhost:8080")
    body_html = load_template("application_approved_user_welcome.html", details)
    body_text = f"Welcome, {details.get('user_name')}! Your application has been approved."
    await invoke_email_sender([details['user_email']], subject, body_html, body_text)

async def invoke_email_sender(recipients: list, subject: str, body_html: str, body_text: str):
    """Prepares payload and invokes the email_sender Lambda."""
    payload = {"recipients": recipients, "subject": subject, "body_html": body_html, "body_text": body_text}
    try:
        logger.info("email_sender.invoke.started", recipient_count=len(recipients))
        lambda_client.invoke(
            FunctionName=os.environ['EMAIL_SENDER_ARN'],
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
    except Exception as e:
        logger.error("email_sender.invoke.failed", exc_info=True)

async def async_handler(event, context):
    """Async handler to route events based on their detail-type."""
    # This assumes the Lambda is triggered by EventBridge
    detail_type = event.get('detail-type')
    detail = event.get('detail', {})

    # Bind AWS Lambda context to all logs for this invocation
    structlog.contextvars.bind_contextvars(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name,
        event_type=detail_type
    )

    if detail_type == "InfectedFileFound":
        await handle_infected_file(detail)
    elif detail_type == "UserApplicationSubmitted":
        await handle_application_submitted(detail)
    elif detail_type == "UserApplicationApproved":
        await handle_application_approved(detail)
    else:
        logger.warning("event.unhandled_type")

def handler(event, context):
    """Synchronous entrypoint for AWS Lambda."""
    logger.info("event.received", full_event=event)
    return asyncio.run(async_handler(event, context))
