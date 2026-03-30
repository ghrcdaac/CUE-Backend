import asyncio
import structlog
from .logic import validate_email_payload, invoke_email_sender, ManualEmailSenderError
from core.logging_config import setup_logging


setup_logging()
logger = structlog.get_logger(__name__)

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)


def handler(event, context):
    """Synchronous entry point for AWS Lambda."""
    return loop.run_until_complete(async_handler(event, context))

async def async_handler(event, context):
    """Asynchronous handler to batch process messages."""
    structlog.contextvars.bind_contextvars(
        aws_request_id=context.aws_request_id,
        function_name=context.function_name
    )

    logger.info(full_event=event) 

    # 1. validate email payload
    try:
        email_payload = await validate_email_payload(event)
    except ManualEmailSenderError as e:
        return {
            "status_code": 400,
            "body": {
              "message": str(e)
            }
        }

    # 2. invoke email sender for valid payload
    try: 
        await invoke_email_sender(email_payload.recipients, email_payload.subject, email_payload.body_html, email_payload.body_text)
        return {
            "status_code": 200,
            "body": {"message": "Successfully invoked email_sender"}
        } 
    except ManualEmailSenderError as e:
        return {
            "status_code":500,
            "body": {"message": str(e)}
        }


