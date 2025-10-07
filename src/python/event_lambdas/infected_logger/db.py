import structlog
from typing import Dict, Any, Optional, Tuple
from uuid import UUID
from asyncpg import Connection
from asyncpg.exceptions import PostgresError, ForeignKeyViolationError

logger = structlog.get_logger(__name__)

async def process_scan_result_in_database(conn: Connection, file_id: UUID, update_data: Dict[str, Any]) -> Tuple[Optional[UUID], str]:
    """
    Atomically updates the file_status with scan results and advances the status using a safe,
    forward-only state machine that correctly handles the scanner/API race condition.

    Returns the collection_id if the file is clean, and the final status.
    """
    target_status = update_data['status']
    
    query = """
        WITH updated AS (
            UPDATE file_status
            SET
                status = (
                    CASE
                        -- This is the critical fix: Allow update if status is 'uploading' OR 'unscanned'.
                        WHEN status IN ('uploading', 'unscanned') AND $2 IN ('clean', 'infected', 'scan_failed')
                            THEN $2::file_status_type
                        -- This handles the standard progression from clean to distributed.
                        WHEN status = 'clean' AND $2 = 'distributed'
                            THEN 'distributed'::file_status_type
                        -- In all other cases (e.g., trying to revert 'distributed' to 'clean'), do nothing.
                        ELSE status
                    END
                ),
                scan_start = $3,
                scan_end = $4,
                scan_results = COALESCE(file_status.scan_results, '[]'::jsonb) || $5::jsonb
            WHERE id = $1
            RETURNING status, id
        )
        SELECT
            u.status,
            -- Only fetch the collection_id if the final status is 'clean'.
            CASE WHEN u.status = 'clean' THEN f.collection_id ELSE NULL END as collection_id
        FROM updated u
        JOIN file f ON u.id = f.id;
    """
    try:
        result = await conn.fetchrow(
            query,
            file_id,
            target_status,
            update_data['scan_start'],
            update_data['scan_end'],
            update_data['scan_results']
        )

        if not result:
            logger.warning("db.scan_update.noop", file_id=str(file_id), target_status=target_status,
                           detail="Status was not advanced. The file may have been in a later state or the ID was invalid.")
            return None, "unchanged"

        final_status = result['status']
        collection_id = result['collection_id']
        
        logger.info("db.scan_update.success", file_id=str(file_id), final_status=final_status)
        return collection_id, final_status

    except ForeignKeyViolationError as e:
        logger.warning(
            "db.scan_update.race_condition",
            file_id=str(file_id),
            detail="The main file record does not exist yet. This is expected; SQS will retry.",
            error=str(e)
        )
        raise  # Re-raise to ensure SQS retries.
    except PostgresError as e:
        logger.error("db.scan_update.postgres_error", file_id=str(file_id), exc_info=True)
        raise

