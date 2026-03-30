import os
import structlog
import boto3
from botocore.exceptions import ClientError
import json
from datetime import datetime
from typing import Optional
from .model import TimeRange
from pydantic import ValidationError

logger = structlog.get_logger(__name__)

class ManualCostUpdateError(Exception):
    pass

async def validate_time_range(time_range:dict):
    try:
        time_range = TimeRange(**time_range)
    except ValidationError as e:
        logger.info("time_range.invalid", exc_info=True)
        raise ManualCostUpdateError(str(e))

    return time_range 

async def invoke_cost_update(start_time:Optional[datetime], end_time:Optional[datetime]):
    """Prepares payload and invokes the email_sender Lambda."""
    payload = {}

    if start_time:
        payload["start_time"] = start_time.isoformat()

    if end_time:
        payload["end_time"] = end_time.isoformat()

    try:
        lambda_client = boto3.client("lambda")
        logger.info("cost_update.invoke.started", payload=payload)
        lambda_client.invoke(
            FunctionName=os.environ['COST_UPDATE_ARN'],
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
        logger.info("cost_update.invoke.completed")
    except Exception:
        logger.error("cost_update.invoke.failed", exc_info=True) 
        raise ManualCostUpdateError("Failed to invoke cost_update")