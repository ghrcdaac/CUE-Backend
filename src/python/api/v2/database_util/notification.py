# File: src/python/api/v2/database_util/notification.py

from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import structlog
import json

logger = structlog.get_logger(__name__)

async def create_notification(
    conn: Connection,
    cueuser_id: UUID,
    params:Tuple) -> Dict[str, Any]:
    """Inserts a new notification record into the database."""
    query = """
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
                "cueuser_id": cueuser_id
            }
            for n in params
        ]
    try:
        return await conn.fetchrow(query, json.dumps(notif_json))
    except UniqueViolationError as e:
        logger.error("db.notification.create.failed_unique", error=str(e))
        raise ValueError("A notification with the same report_type already exists for this user.") from e
    except ForeignKeyViolationError as e:
        logger.error("db.notification.create.failed_fk", error=str(e))
        raise ValueError("The specified cueuser_id does not exist.") from e

async def get_notification_by_id(conn: Connection, notification_id: UUID) -> Optional[Dict[str, Any]]:
    """Retrieves a notification record from the database by its ID."""
    return await conn.fetchrow("SELECT * FROM notification WHERE id = $1", notification_id)

async def list_notifications_by_user(conn: Connection, requesting_user: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Retrieves all notifications for a given user."""
    return await conn.fetch("SELECT * FROM notification WHERE cueuser_id = $1 ORDER BY created_time DESC", requesting_user.get('id', 0))

async def update_notification(
    conn: Connection,
    notification_id: UUID,
    update_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Updates an existing notification record in the database."""
    fields, values = list(update_data.keys()), list(update_data.values())
    set_clause = ", ".join(f"{field} = ${i+1}" for i, field in enumerate(fields))
    query = f"""
        UPDATE notification
        SET {set_clause}, updated_time = now()
        WHERE id = ${len(fields) + 1} AND report_type = ${len(fields) + 2}
        RETURNING *;
    """
    try:
        return await conn.fetchrow(query, *values, notification_id)
    except ForeignKeyViolationError as e:
        logger.error("db.notification.update.failed_fk", error=str(e))
        raise ValueError("The specified cueuser_id does not exist.") from e

async def delete_notification(conn: Connection, notification_id: UUID) -> bool:
    """Deletes a notification record from the database by its ID."""
    try:
        result = await conn.execute("DELETE FROM notification WHERE id = $1", notification_id)
        return result.strip() == "DELETE 1"
    except ForeignKeyViolationError as e:
        logger.warning("db.notification.delete.failed_fk", notification_id=str(notification_id), error=str(e))
        raise ValueError("Cannot delete this notification because it is still linked to other records.") from e
