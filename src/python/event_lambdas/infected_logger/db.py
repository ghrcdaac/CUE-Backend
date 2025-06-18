# --- src/python/event_lambdas/infected_logger/db.py ---
import logging
from typing import Dict, Any
from uuid import UUID

from asyncpg import Connection
from asyncpg.exceptions import PostgresError

# Re-using the robust, centralized db utility function
from lambda_utils.database_util.file_status import update_file_status_in_db

logger = logging.getLogger(__name__)

# NEW: A custom exception to make our logic clearer.
class RecordNotFoundError(Exception):
    """Raised when a database record cannot be found for an update."""
    pass

async def update_scan_status_in_database(conn: Connection, file_id: UUID, update_data: Dict[str, Any]) -> bool:
    """
    Updates the file_status record in the database for a given file_id.

    Args:
        conn: An active asyncpg database connection.
        file_id: The UUID of the file to update.
        update_data: A dictionary containing the fields to update.

    Returns:
        True if the update was successful.
    
    Raises:
        RecordNotFoundError: If the file_id does not exist in the database.
    """
    try:
        params = (update_data, file_id)
        result = await update_file_status_in_db(conn, params)
        
        # MODIFIED: If the database function returns no result, it means the row
        # was not found. We now raise a specific error to signal this failure.
        if not result:
            raise RecordNotFoundError(f"File status record not found for ID {file_id}")
        
        logger.info(f"Successfully updated file status for ID {file_id}.")
        return True

    except PostgresError as e:
        logger.error(f"Database error while updating file status for {file_id}: {e}", exc_info=True)
        raise # Re-raise database errors
    except Exception as e:
        logger.error(f"An unexpected error occurred during database operation for {file_id}: {e}", exc_info=True)
        raise # Re-raise other unexpected errors
