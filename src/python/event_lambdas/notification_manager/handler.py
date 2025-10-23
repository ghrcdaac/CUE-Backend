import asyncio
import json
import os
import boto3
import structlog
from pathlib import Path
from uuid import UUID
from datetime import timedelta
import asyncpg

from core.logging_config import setup_logging
from core.db_pool import get_database_pool
from db import (
    get_infected_file_details, 
    get_new_application_details, 
    get_approved_user_details,
    get_infected_scheduled_file_details,
    get_providers_exceeding_threshold,
    get_ngroup_recipient_emails,
    mark_files_as_notified, 
    mark_providers_as_notified
)
from logic import process_infected_scheduled_notification 

setup_logging()
logger = structlog.get_logger(__name__)


try:
    loop = asyncio.get_running_loop()
except RuntimeError: 
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

lambda_client = boto3.client('lambda')


# Read configurable thresholds from environment variables
# Defaults to 30 minutes if not set
NOTIFICATION_SCHEDULE_MINUTES = int(os.getenv("NOTIFICATION_SCHEDULE_MINUTES", "30"))
# Defaults to 5 files if not set
INFECTED_FILE_THRESHOLD = int(os.getenv("INFECTED_FILE_THRESHOLD", "5"))
# Defaults to 24 hours if not set (MUST MATCH infected_logger)
BLOCKING_LOOKBACK_HOURS = int(os.getenv("BLOCKING_LOOKBACK_HOURS", "24"))



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

async def handle_infected_file(detail: dict, pool: asyncpg.Pool):
    """Handles logic for the original infected file notification."""

    file_id = UUID(detail['key'])
    logger.info("event.infected_file.received", file_id=str(file_id))
    
    async with pool.acquire() as conn:
        db_details = await get_infected_file_details(conn, file_id)

    if not db_details or not db_details.get('recipient_emails'):
        logger.warning("notification.recipients.not_found", alert_type="infected_file", file_id=str(file_id))
        return
    
    scan_results = detail.get('scanResults', [])
    virus_names = ", ".join(
        finding['virusName'][0] for finding in scan_results if finding.get('virusName')
    ) or "N/A"

    template_context = {
        "file_id": detail.get('key'),
        "file_name": db_details.get('file_name', 'N/A'),
        "uploader_name": db_details.get('uploader_name', 'N/A'),
        "collection_name": db_details.get('collection_name', 'N/A'),
        "date_scanned": detail.get('dateScanned', 'N/A'),
        "scan_result": detail.get('result', 'N/A'),
        "virus_names": virus_names
    }
    
    subject = f"CUE Security Alert: Infected File Detected - {db_details.get('file_name', str(file_id))}"
    body_html = load_template("infected_file_template.html", template_context)
    body_text = f"An infected file was detected: {db_details.get('file_name')}"
    await invoke_email_sender(db_details['recipient_emails'], subject, body_html, body_text)

async def handle_infected_files_scheduled(detail: dict, pool):
    logger.info("event.scheduled_infected_files.received", detail=detail)

    # This is for the "providers blocked in last 1h" report
    provider_lookback_window = timedelta(hours=BLOCKING_LOOKBACK_HOURS)
    infected_file_threshold = INFECTED_FILE_THRESHOLD 
    
    logger.info(
        "scheduler.settings.loaded",
        provider_lookback_hours=BLOCKING_LOOKBACK_HOURS,
        infected_file_threshold=infected_file_threshold
    )

    notification_details = None
    providers_exceeding = None

    async with pool.acquire() as conn:
        # 1. Fetch all pending notifications (files and providers)
        # We no longer pass time_threshold to get_infected_scheduled_file_details
        notification_details = await get_infected_scheduled_file_details(conn)
        providers_exceeding = await get_providers_exceeding_threshold(conn, provider_lookback_window, infected_file_threshold)

        # 2. Extract the IDs of what we just found
        file_ids_to_mark = [
            file['file_id'] 
            for ngroup_data in (notification_details or {}).values() 
            for file in ngroup_data.get('file_details', [])
        ]
        
        provider_ids_to_mark = [
            provider['provider_id'] 
            for ngroup_data in (providers_exceeding or {}).values() 
            for provider in ngroup_data
        ]

        # 3. Check if there is anything to do
        if not file_ids_to_mark and not provider_ids_to_mark:
            logger.info("No new infected files or provider blocks to report.")
            return # Nothing to do

        # 4. Atomically "claim" these records by marking them in a transaction
        try:
            async with conn.transaction():
                if file_ids_to_mark:
                    await mark_files_as_notified(conn, file_ids_to_mark)
                if provider_ids_to_mark:
                    await mark_providers_as_notified(conn, provider_ids_to_mark)
            logger.info("Successfully claimed notifications.", 
                        files=len(file_ids_to_mark), 
                        providers=len(provider_ids_to_mark))
        except Exception as e:
            logger.error("Failed to claim notifications in transaction, will retry on next run.", exc_info=True)
            # We re-raise to fail the lambda, so it retries.
            # The records weren't marked, so they'll be picked up next time.
            raise

    if not notification_details:
        logger.info("No infected file notifications to send")
        # ---  Check if there are providers to report even if no new files ---
        if not providers_exceeding:
             return None # Exit if nothing to report
        else: # Prepare to send email only about providers exceeding threshold
             notification_details = {} # Ensure loop below runs correctly if needed
             logger.info("Providers exceeded threshold, but no new file details. Preparing provider report.")

    processed_ngroups = set() # Keep track of ngroups processed via file details

    # Process ngroups that had infected files
    if notification_details:
        for ngroup_id, infected_file_details in notification_details.items():
            processed_ngroups.add(ngroup_id) # Mark as processed
            logger.info(f"Processing infected file notification for ngroup: {ngroup_id}")
            # Get the list of providers exceeding threshold for *this specific ngroup*
            provider_report_details = providers_exceeding.get(ngroup_id, []) # Use empty list if none for this group
            
            subject, html_details, body_text = await process_infected_scheduled_notification(
                infected_file_details, 
                provider_report_details # Pass the list for this group
            )
            body_html = load_template("infected_files_template.html", html_details)
            # Use recipient emails from infected_file_details as before
            await invoke_email_sender(infected_file_details.get('recipient_emails', []), subject, body_html, body_text)

    # --- Process ngroups that *only* had providers exceeding threshold ---
    for ngroup_id, provider_report_details in providers_exceeding.items():
        if ngroup_id not in processed_ngroups:
            logger.info(f"Processing provider-only notification for ngroup: {ngroup_id}")
            # Need recipient emails and short_name for this ngroup
            async with pool.acquire() as conn:
                # ---  Get both emails and short_name ---
                recipient_emails, ngroup_short_name = await get_ngroup_recipient_emails(conn, ngroup_id) 

            if not recipient_emails:
                 logger.warning("No recipients found for provider-only report", ngroup_id=ngroup_id)
                 continue

            # ---  Use the fetched short_name ---
            # Use the actual short_name or fallback if None was returned
            actual_short_name = ngroup_short_name or 'Unknown Group' 
            minimal_infected_details = {
                'short_name': actual_short_name, 
                'file_details': [], 
                'recipient_emails': recipient_emails
            }

            subject, html_details, body_text = await process_infected_scheduled_notification(
                minimal_infected_details, # Pass minimal file info with correct name
                provider_report_details # Pass the provider list
            )
            # Update subject to reflect no files, just provider issues, using correct name
            subject = f"CUE Security Alert: Providers Exceeded Infected File Threshold - {actual_short_name}" 
            html_details['header'] = subject # Update header in details

            body_html = load_template("infected_files_template.html", html_details)
            await invoke_email_sender(recipient_emails, subject, body_html, body_text)

async def handle_application_submitted(detail: dict, pool: asyncpg.Pool):
    """Handles sending a notification to admins about a new application."""
 
    app_id = UUID(detail["application_id"])
    logger.info("event.application_submitted.received", application_id=str(app_id))
    
    async with pool.acquire() as conn:
        details = await get_new_application_details(conn, app_id)
        
    if not details or not details.get('recipient_emails'):
        logger.warning("notification.recipients.not_found", alert_type="application_submitted", application_id=str(app_id))
        return
    
    # Template selection logic for security applications
    ESDIS_SECURITY_NGROUP_ID = UUID('0259fb55-1146-4461-ade2-57504e0c3ace')
    if details.get('ngroup_id') == ESDIS_SECURITY_NGROUP_ID:
        template_name = "new_security_application_alert.html"
        subject = f"ACTION REQUIRED: New CUE Security Application"
    else:
        template_name = "new_application_admin_alert.html"
        subject = f"New CUE User Application for {details.get('ngroup_name', 'N/A')}"

    body_html = load_template(template_name, details)
    body_text = f"A new user application from {details.get('user_name')} has been submitted."
    await invoke_email_sender(details['recipient_emails'], subject, body_html, body_text)

async def handle_application_approved(detail: dict, pool: asyncpg.Pool):
    """Handles sending a welcome email to a newly approved user."""

    user_id = UUID(detail["user_id"])
    logger.info("event.application_approved.received", user_id=str(user_id))
    
    async with pool.acquire() as conn:
        details = await get_approved_user_details(conn, user_id)
        
    if not details:
        logger.warning("notification.user_details.not_found", alert_type="application_approved", user_id=str(user_id))
        return
        
    subject = "Welcome to the CUE System!"
    details["dashboard_url"] = os.getenv("FRONTEND_URL", "http://localhost:3000")
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

    pool = await get_database_pool()
    if not pool:
        logger.critical("db.pool.not_available.failing_invocation")
        raise RuntimeError("Database connection pool is not available.")

    detail_type = event.get('detail-type')
    detail = event.get('detail', {})

    structlog.contextvars.bind_contextvars(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name,
        event_type=detail_type
    )

    if detail_type == "InfectedFileFound":
        # await handle_infected_file(detail, pool)
        pass # Explicitly pass
    elif detail_type == "ScheduledInfectedFileFound":
        await handle_infected_files_scheduled(detail, pool)
    elif detail_type == "UserApplicationSubmitted":
        await handle_application_submitted(detail, pool)
    elif detail_type == "UserApplicationApproved":
        await handle_application_approved(detail, pool)
    else:
        logger.warning("event.unhandled_type")

def handler(event, context):
    """Synchronous entrypoint for AWS Lambda."""

    try:
        logger.info("event.received", full_event=event)
        loop.run_until_complete(async_handler(event, context))
    except Exception:
        logger.critical("lambda.handler.unhandled_exception", exc_info=True)
        raise