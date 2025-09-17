import json
import os
import boto3
from botocore.exceptions import ClientError
import structlog
from core.logging_config import setup_logging

# Initialize structured logging at the module level
setup_logging()
logger = structlog.get_logger(__name__)

# Reusable boto3 client (initialized once per container)
ses_client = None

def get_ses_client():
    """Initializes and returns a reusable SES client."""
    global ses_client
    if ses_client is None:
        region = os.environ['SES_REGION']
        logger.info("ses.client.initializing", region=region)
        ses_client = boto3.client('ses', region_name=region)
    return ses_client

def handler(event, context):
    """
    Receives a payload with recipients, subject, and body, and sends an email via AWS SES.
    """
    # Bind Lambda context to all logs for this invocation
    structlog.contextvars.bind_contextvars(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name
    )
    logger.info("event.received", full_event=event)

    try:
        # Load required configuration from environment variables
        sender_email = os.environ['SENDER_EMAIL']
        source_arn = os.environ.get('SOURCE_ARN') # Optional for flexibility
        configuration_set_name = os.environ.get('CONFIGURATION_SET_NAME') # Optional

        # Validate input payload
        recipients = event['recipients']
        subject = event['subject']
        body_html = event['body_html']
        body_text = event['body_text']

        if not all([recipients, subject, body_html, body_text]):
            logger.error("event.payload.invalid", reason="Missing required fields")
            return {"statusCode": 400, "body": "Invalid payload: 'recipients', 'subject', 'body_html', and 'body_text' are required."}

    except KeyError as e:
        logger.error("event.payload.invalid", missing_key=str(e))
        return {"statusCode": 400, "body": f"Missing required key in payload: {e}"}
    except Exception as e:
        logger.error("configuration.error", error=str(e), exc_info=True)
        return {"statusCode": 500, "body": f"Internal configuration error: {e}"}

    # Construct the payload for the SES API call
    message_payload = {
        'Body': {'Html': {'Data': body_html}, 'Text': {'Data': body_text}},
        'Subject': {'Data': subject},
    }
    
    send_email_args = {
        "Source": sender_email,
        "Destination": {'ToAddresses': recipients},
        "Message": message_payload,
    }

    # Conditionally add optional parameters if they exist. check
    if source_arn:
        send_email_args["SourceArn"] = source_arn
    if configuration_set_name:
        send_email_args["ConfigurationSetName"] = configuration_set_name

    try:
        client = get_ses_client()
        response = client.send_email(**send_email_args)
        
        logger.info("email.sent.success", message_id=response['MessageId'], recipients=recipients)
        return {'statusCode': 200, 'body': json.dumps({'messageId': response['MessageId']})}

    except ClientError as e:
        logger.error(
            "ses.send_email.failed", 
            error_code=e.response['Error']['Code'], 
            error_message=e.response['Error']['Message'],
            exc_info=True
        )
        # Re-raising the exception allows AWS Lambda to handle the failure,
        # potentially moving it to a Dead Letter Queue (DLQ) if configured.
        raise

