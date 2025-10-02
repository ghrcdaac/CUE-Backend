import structlog
from typing import Dict, Any
from uuid import UUID
import json

from asyncpg import Connection
from asyncpg.exceptions import PostgresError, ForeignKeyViolationError

logger = structlog.get_logger(__name__)

async def upsert_scan_status_in_database(conn: Connection, file_id: UUID, update_data: Dict[str, Any]) -> bool:
    """
    Atomically updates a file_status record if it exists, or inserts it if it does not.
    This is known as an "UPSERT" operation.
    """
    upsert_query = """
        INSERT INTO file_status (id, status, scan_start, scan_end, scan_results)
        VALUES ($1, $2::file_status_type, $3, $4, $5::jsonb)
        ON CONFLICT (id) DO UPDATE SET
            status = EXCLUDED.status,
            scan_start = EXCLUDED.scan_start,
            scan_end = EXCLUDED.scan_end,
            scan_results = COALESCE(file_status.scan_results, '[]'::jsonb) || EXCLUDED.scan_results
        RETURNING id;
    """
    try:
        params = (
            file_id,
            update_data['status'],
            update_data['scan_start'],
            update_data['scan_end'],
            update_data['scan_results']
        )
        
        result = await conn.fetchrow(upsert_query, *params)
        
        if not result:
            logger.error("db.upsert.failed", file_id=str(file_id), reason="Query failed to return an ID.")
            return False
        
        logger.info("db.upsert.success", file_id=str(file_id))
        return True

    except ForeignKeyViolationError as e:
        # This is an expected race condition if the Lambda runs before the API.
        # Log it as a warning and then re-raise the exception.
        # SQS will see the failure and automatically retry the message later.
        logger.warning(
            "db.upsert.race_condition",
            file_id=str(file_id),
            detail="The main file record does not exist yet. This is expected behavior; SQS will retry.",
            error=str(e)
        )
        raise # Re-raise to ensure SQS retries the message.

    except PostgresError as e:
        logger.error("db.upsert.postgres_error", file_id=str(file_id), exc_info=True)
        raise
    except Exception as e:
        logger.error("db.upsert.unexpected_error", file_id=str(file_id), exc_info=True)
        raise

async def get_collection_id(conn: Connection, file_id: UUID) -> UUID:
    query = "SELECT f.collection_id FROM file f where id = $1"
    try:
        result = await conn.fetchval(query, file_id)
        return UUID(str(result))
    except PostgresError as e:
        logger.error("db.get_collection_id.postgres_error", file_id=str(file_id), exc_info=True)
        raise
    except Exception as e:
        logger.error("db.get_collection_id.unexpected_error", file_id=str(file_id), exc_info=True)
        raise