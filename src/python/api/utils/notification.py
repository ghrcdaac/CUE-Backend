from asyncpg.pool import Pool

from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import notification as notification_db
from lambda_utils.type_util.notification import Notification, NotificationCreate, NotificationReturn

from uuid import UUID
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class NotificationNotFoundError(Exception):
    def __init__(self, privilege: str):
        super().__init__(f"Notification not found: {privilege}")
        self.privilege = privilege

async def create_notifications(notifications: List[Notification], user_id: UUID) -> List[NotificationReturn]:
    """Creates a new notification record."""
    pool: Pool = await get_connection_pool()
    params = (notifications, user_id)
    try:
        result = await query(pool, notification_db.create_notifications, params, row_mapper=NotificationReturn.from_db_row)
        return result
    except Exception as e:
        logger.error(f"Error creating notification: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_notification(notification_id: UUID) -> NotificationReturn:
    """get a notification record."""
    pool: Pool = await get_connection_pool()
    params = (notification_id,)
    try:
        result = await query(pool, notification_db.get_notification_from_db, params, row_mapper=NotificationReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise NotificationNotFoundError(notificaiton_id=notification_id)
    except Exception as e:
        logger.error(f"Error getting collection: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_notification_by_user_id(user_id: UUID) -> List[NotificationReturn]:
    pool: Pool = await get_connection_pool()
    params = (user_id,)
    try:
        result = await query(pool, notification_db.get_notification_by_user_id, params, row_mapper=NotificationReturn.from_db_row)
        return result
        
    except Exception as e:
        logger.error(f"Error getting notification: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def update_notification(notification_id: UUID, data: Notification) -> NotificationReturn:
    pool: Pool = await get_connection_pool()
    params = (notification_id, data.report_type, data.frequency)
    try:
        result = await query(pool, notification_db.update_notification, params, row_mapper=NotificationReturn.from_db_row)
        if result:
            return result[0]
        else:
           raise NotificationNotFoundError(notificaiton_id=notification_id)
    except Exception as e:
        logger.error(f"Error updating notification: {e}", exc_info=True)
        raise
    finally:
        await pool.close()