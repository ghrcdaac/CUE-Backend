from v2.type_util.events import FilePayload, FileTransferResponse
from v2.type_util.auth import AuthUser
import boto3
from botocore.exceptions import ClientError
import os
import structlog
import json

logger = structlog.get_logger(__name__)

class EventError(Exception):
    """Custom exception raised when manual event encounters error."""
    pass

def _get_lambda_client():
    return boto3.client("lambda", region_name=os.environ.get('AWS_REGION')) 

async def trigger_manual_file_transfer(payload: FilePayload, user: AuthUser) -> FileTransferResponse:
    """Trigger manual file transfer lambda function"""

    try:
        payload_json = payload.model_dump_json()
        logger.info("manual_file_transfer.invoke.starting", user=str(user.id), payload=payload_json)
        lambda_client = _get_lambda_client()
        response = lambda_client.invoke(
            FunctionName=os.environ['MAN_TRANSFER_LAMBDA_NAME'],
            InvocationType='RequestResponse', #synchronous invocation to get response
            Payload=payload_json
        )
    except ClientError as e:
        logger.error("manual_file_transfer.invoke.failed", payload=payload, error=str(e))
        raise EventError("Failed to invoke manual file transfer")
    except Exception as e:
        logger.error("manual_file_transfer.invoke.failed.unexpected_error",  error=str(e))
        raise e

    try:
        response_payload = response.get('Payload').read().decode('utf-8')
        aws_request_id = response.get('ResponseMetadata',{}).get("RequestId")
        logger.info("manual_file_transfer.invoke.complete",
                    aws_request_id=aws_request_id)
        response_payload_json = json.loads(response_payload)
        return response_payload_json
    except json.JSONDecodeError as e:
        logger.error('manual_file_transfer.payload_parsing.failed', response_payload=response_payload, error=str(e))
        raise EventError("Response payload invalid.")
