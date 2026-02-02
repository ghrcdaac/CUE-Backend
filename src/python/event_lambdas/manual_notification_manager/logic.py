import os
import structlog
import boto3
from typing import Union
from datetime import datetime
import asyncpg 
import json
from uuid import UUID
from .model import Notification
from .db import (
    check_pending_user_application_pending,
    check_user_application_approved,
    check_infected_file_exists
)
from pydantic import ValidationError

logger = structlog.get_logger(__name__)

class ManualNotificationError(Exception):
    pass

async def validate_notification(pool: asyncpg.Pool, notification: dict):
    try:
        parsed_notification = Notification(**notification)
    except ValidationError as e:
        logger.error("notification.parsing.failed", exc_info=True)
        raise ManualNotificationError(str(e))

    async with pool.acquire() as conn:
        if parsed_notification.detail_type == "UserApplicationSubmitted":
            if not await check_pending_user_application_pending(conn, UUID(parsed_notification.detail.get("application_id"))):
                logger.error("User Application is not pending", exc_info=True)
                raise ManualNotificationError("Invalid Application ID")

        if parsed_notification.detail_type == "UserApplicationApproved":
            if not await check_user_application_approved(conn, UUID(parsed_notification.detail.get("user_id"))):
                logger.error("User Application is not approved", exc_info=True)
                raise ManualNotificationError("User ID is not approved")

        if parsed_notification.detail_type == "InfectedFileFound":
            if not await check_infected_file_exists(conn, UUID(parsed_notification.detail.get("key"))):
                logger.error("File ID is not infected", exc_info=True)
                raise ManualNotificationError("File ID is not infected")

    return parsed_notification

async def invoke_notification_manager(detail_type: str, detail: Union[dict, datetime]):
    """Prepares payload and invokes the notification_manager Lambda."""

    payload = {"detail-type": detail_type, "detail": detail}
    try:
        lambda_client = boto3.client("lambda")
        logger.info("notification_manager.invoke.started", payload=payload)
        lambda_client.invoke(
            FunctionName=os.environ['NOTIFICATION_MANAGER_ARN'],
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
        logger.info("notification_manager.invoke.completed")
    except Exception: 
        logger.error("notification_manager.invoke.failed", exc_info=True)
        raise ManualNotificationError("Failed to invoke notification manager")