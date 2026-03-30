import os
import boto3
import json
import structlog
from model import EmailPayload
from pydantic import ValidationError

lambda_client = boto3.client('lambda')
logger = structlog.get_logger(__name__)

class ManualEmailSenderError(Exception):
    pass

async def validate_email_payload(event: EmailPayload):
    try:
        email_payload = EmailPayload(**event)
        return email_payload
    except ValidationError as e:
        logger.error("email_payload.invalid", exc_info=True)
        raise ManualEmailSenderError(str(e))

async def invoke_email_sender(recipients: list, subject: str, body_html: str, body_text: str):
    """Prepares payload and invokes the email_sender Lambda."""

    payload = {"recipients": recipients, "subject": subject, "body_html": body_html, "body_text": body_text}
    try:
        logger.info("email_sender.invoke.started", payload=payload)
        lambda_client.invoke(
            FunctionName=os.environ['EMAIL_SENDER_ARN'],
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
        logger.info("email_sender.invoke.completed")
    except Exception:
        logger.error("email_sender.invoke.failed", exc_info=True)
        raise ManualEmailSenderError("Failed to invoke email sender")