# ==============================================================================
# File: src/python/api/v2/utils/notification.py
# --- Updated to v2 style with request-based DB connection and structlog ---
# ==============================================================================

from uuid import UUID
from typing import List, Dict, Any
import structlog
from fastapi import Request

from v2.type_util.auth import AuthUser
from v2.database_util import notification as notification_db
from v2.type_util.notification import Notification

logger = structlog.get_logger(__name__)

class NotificationNotFoundError(Exception):
    """Custom exception raised when a notification is not found."""
    def __init__(self, notification_id: UUID):
        self.notification_id = notification_id
        super().__init__(f"Notification not found with ID: {notification_id}")

async def create_notification(request: Request, user: AuthUser, notifications: List[Notification]) -> List[Dict[str, Any]]:
    """Creates a new notification record for a user."""
    async with request.state.pool.acquire() as conn:
        requesting_user=user.model_dump()
        record = await notification_db.create_notification(
            conn,
            requesting_user,
            tuple(notifications)
        )
    logger.info("notification.created for", cueuser_id=requesting_user.get('first_name', ''))
    return dict(record)

async def get_notification(request: Request, notification_id: UUID) -> Dict[str, Any]:
    """Retrieve a notification record by its ID."""
    async with request.state.pool.acquire() as conn:
        record = await notification_db.get_notification_by_id(conn, notification_id)
    if not record:
        raise NotificationNotFoundError(notification_id)
    return dict(record)

async def list_notifications_by_user(request: Request, user: AuthUser) -> List[Dict[str, Any]]:
    """Retrieve all notifications for a given user."""
    async with request.state.pool.acquire() as conn:
        requesting_user=user.model_dump()
        records = await notification_db.list_notifications_by_user(conn, requesting_user)
    return [dict(r) for r in records]

async def update_notification(
    request: Request,
    notification_id: UUID,
    data: Notification
) -> Dict[str, Any]:
    """Update an existing notification record."""
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")

    async with request.state.pool.acquire() as conn:
        record = await notification_db.update_notification(conn, notification_id, update_data)

    if not record:
        raise NotificationNotFoundError(notification_id)

    logger.info("notification.updated", notification_id=str(notification_id))
    return dict(record)

async def delete_notification(request: Request, notification_id: UUID):
    """Delete a notification record."""
    async with request.state.pool.acquire() as conn:
        success = await notification_db.delete_notification(conn, notification_id)
    if not success:
        raise NotificationNotFoundError(notification_id)
    logger.info("notification.deleted", notification_id=str(notification_id))
