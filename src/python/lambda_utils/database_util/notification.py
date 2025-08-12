from asyncpg import Connection, UniqueViolationError, DataError
from typing import Tuple, List
import json
from lambda_utils.type_util.notification import NotificationReturn
import logging

logger = logging.getLogger(__name__)

class NotificationNotFoundError(Exception):
    def __init__(self, privilege: str):
        super().__init__(f"Notification not found: {privilege}")
        self.privilege = privilege

async def create_notifications(conn: Connection, params:Tuple) -> List[NotificationReturn]:
    insert_query = """
        INSERT INTO notification (cueuser_id, report_type, frequency, created_time, updated_time)
        SELECT x.cueuser_id, x.report_type, x.frequency, now(), now()
        FROM jsonb_to_recordset($1::jsonb) AS x(
            cueuser_id uuid,
            report_type report_type,
            frequency report_frequency
        )
        RETURNING id, cueuser_id, report_type, frequency, created_time, updated_time
    """
    notif_json = [
            {
                **n.dict(),
                "cueuser_id": str(params[1])
            }
            for n in params[0]
        ]
    try:
        return await conn.fetch(insert_query, json.dumps(notif_json))
    except UniqueViolationError as e:
        logger.error(f"Failed to create notification due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A user with the given id already exists.")
    except DataError as e:
        logger.error(f"Failed to create notification due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating a notification.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating a notification: {e}", exc_info=True)
        raise

async def get_notification_from_db(conn: Connection, params: Tuple) -> NotificationReturn:
    """get notification entry based on id"""
    select_query = """
        SELECT * from notification 
        WHERE id = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching the notification: {e}", exc_info=True)
        raise

async def get_notification_by_user_id(conn: Connection, params: Tuple) -> List[NotificationReturn]:
    """get notification entry based on id"""
    select_query = """
        SELECT * from notification 
        WHERE cueuser_id = $1
    """
    try:
        result = await conn.fetch(select_query, *params)
        return result
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching the notification: {e}", exc_info=True)
        raise

async def update_notification(conn: Connection, params: Tuple) -> NotificationReturn:
    """Updates an existing privilege record in the database."""
    update_query = """
        UPDATE notification
        SET frequency = $3, updated_time = now()
        WHERE id = $1 AND report_type = $2
        RETURNING *
    """
    try:
        return await conn.fetch(update_query, *params)
    except DataError as e:
        logger.error(f"Failed to update notification due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for updating a notification.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating a notification: {e}", exc_info=True)
        raise