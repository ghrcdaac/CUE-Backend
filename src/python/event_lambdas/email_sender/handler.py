import json
import logging
import os
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# Initialize client once per container for reuse
ses_client = None

def get_ses_client():
    """Initializes and returns a reusable SES client."""
    global ses_client
    if ses_client is None:
        region = os.environ['SES_REGION']
        logger.info(f"Initializing SES client for region: {region}")
        ses_client = boto3.client('ses', region_name=region)
    return ses_client

def handler(event, context):
    """
    Receives a payload with recipients, subject, and body, and sends an email.
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Load required configuration
    sender_email = os.environ['SENDER_EMAIL']
    source_arn = os.environ['SOURCE_ARN']
    configuration_set_name = os.environ['CONFIGURATION_SET_NAME']

    # Validate input payload
    recipients = event.get('recipients')
    subject = event.get('subject')
    body_html = event.get('body_html')
    body_text = event.get('body_text')

    if not all([recipients, subject, body_html, body_text]):
        error_msg = "Invalid payload: 'recipients', 'subject', 'body_html', and 'body_text' are required."
        logger.error(error_msg)
        raise ValueError(error_msg)

    message_payload = {
        'Body': {'Html': {'Data': body_html}, 'Text': {'Data': body_text}},
        'Subject': {'Data': subject},
    }

    try:
        client = get_ses_client()
        response = client.send_email(
            Source=sender_email,
            Destination={'ToAddresses': recipients},
            Message=message_payload,
            SourceArn=source_arn,
            ConfigurationSetName=configuration_set_name
        )
        logger.info(f"Email sent successfully! Message ID: {response['MessageId']}")
        return {'status': 'success', 'messageId': response['MessageId']}
    except ClientError as e:
        logger.error(f"Failed to send email: {e.response['Error']['Message']}", exc_info=True)
        raise  # Re-raise to signal failure
