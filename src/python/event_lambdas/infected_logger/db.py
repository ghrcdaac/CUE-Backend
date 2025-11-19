import structlog
from typing import Dict, Any, Optional, Tuple, List 
from uuid import UUID
from asyncpg import Connection
from asyncpg.exceptions import PostgresError, ForeignKeyViolationError
from datetime import timedelta 

logger = structlog.get_logger(__name__)


async def process_scan_result_in_database(conn: Connection, file_id: UUID, update_data: Dict[str, Any]) -> Tuple[Optional[UUID], str, Optional[UUID]]:
    """
    Atomically updates the file_status with scan results and advances the status.
    Returns the collection_id (if clean), the final status, and the provider_id
    associated with the file's collection.
    """
    target_status = update_data['status']
    
    query = """
        WITH updated AS (
            UPDATE file_status
            SET
                status = (
                    CASE
                        WHEN status IN ('uploading', 'unscanned') AND $2 IN ('clean', 'infected', 'scan_failed')
                            THEN $2::file_status_type
                        WHEN status = 'clean' AND $2 = 'distributed'
                            THEN 'distributed'::file_status_type
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
            CASE WHEN u.status = 'clean' THEN f.collection_id ELSE NULL END as collection_id,
            c.provider_id -- Select the provider_id from the collection
        FROM updated u
        JOIN file f ON u.id = f.id
        JOIN collection c ON f.collection_id = c.id; -- Join collection to get its provider_id
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
                           detail="Status not advanced or ID invalid.")
            return None, "unchanged", None # Return None for provider_id

        final_status = result['status']
        collection_id = result['collection_id']
        provider_id = result['provider_id'] # Get collection's provider_id
        
        logger.info("db.scan_update.success", file_id=str(file_id), final_status=final_status, collection_provider_id=str(provider_id) if provider_id else "N/A")
        return collection_id, final_status, provider_id # Return collection's provider_id

    except ForeignKeyViolationError as e:
        logger.warning(
            "db.scan_update.race_condition_or_fk_issue", file_id=str(file_id),
            detail="File/Collection record missing or FK violation. SQS will retry.", error=str(e)
        )
        raise
    except PostgresError as e:
        logger.error("db.scan_update.postgres_error", file_id=str(file_id), exc_info=True)
        raise



async def count_provider_infected_files(conn: Connection, provider_id: UUID, lookback_window: timedelta) -> int:
    """Counts infected files associated with collections linked to a specific provider."""
    query = """
        SELECT COUNT(f.id)
        FROM file f
        JOIN file_status fs ON f.id = fs.id
        JOIN collection c ON f.collection_id = c.id -- Join file to collection
        WHERE c.provider_id = $1 -- Filter by collection's provider_id
          AND fs.status = 'infected'
          AND fs.scan_end >= (NOW() - $2::INTERVAL);
    """
    try:
        count = await conn.fetchval(query, provider_id, lookback_window)
        logger.info("db.provider_infected_count.success (by collection)", provider_id=str(provider_id), lookback_window=str(lookback_window), count=count)
        return count or 0
    except Exception as e:
        logger.error("db.provider_infected_count.failed (by collection)", provider_id=str(provider_id), exc_info=True)
        return 0 # Return 0 on error to prevent accidental blocking


async def block_provider_instant(conn: Connection, provider_id: UUID, reason: str):
    """Sets can_upload to false and updates the reason for a single provider."""
    query = """
        UPDATE provider
        SET 
            can_upload = false,
            reason = $2
        WHERE id = $1 AND can_upload = true; -- Only update if not already blocked
    """
    try:
        result = await conn.execute(query, provider_id, reason)
        # Check if a row was actually updated
        if result == "UPDATE 1":
             logger.info("db.provider_block.success", provider_id=str(provider_id), reason=reason)
             return True
        elif result == "UPDATE 0":
             logger.info("db.provider_block.already_blocked", provider_id=str(provider_id))
             return False # Indicate no change was made
        else:
             logger.warning("db.provider_block.unexpected_result", provider_id=str(provider_id), result=result)
             return False
    except Exception as e:
        logger.error("db.provider_block.failed", provider_id=str(provider_id), exc_info=True)
        return False # Indicate failure