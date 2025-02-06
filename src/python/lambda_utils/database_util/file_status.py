from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError, DataError
from typing import Tuple, List, Optional
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

async def create_file_status_in_db(conn: Connection, params: Tuple) -> List:
    """Inserts a new file_status record into the database."""
    insert_query = """
        INSERT INTO file_status (id, upload_time, status, scan_results)
        VALUES ($1, $2, $3::file_status_type, $4::jsonb)
        RETURNING id, upload_time, scan_start, scan_end, egress_start, status, scan_results
    """
    try:
        return await conn.fetch(insert_query, *params)
    except UniqueViolationError as e:
        logger.error(f"Failed to create file_status due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A file_status record with the given ID already exists.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to create file_status due to foreign key violation: {e}", exc_info=True)
        raise ValueError("Invalid id provided.") from e
    except DataError as e:
        logger.error(f"Failed to create file_status due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating a file_status record.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating a file_status record: {e}", exc_info=True)
        raise

async def get_file_status_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves a file_status record from the database by its id (which is now the PK)."""
    select_query = """
        SELECT id, upload_time, scan_start, scan_end, egress_start, status, scan_results
        FROM file_status
        WHERE id = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting a file_status record: {e}", exc_info=True)
        raise

async def update_file_status_in_db(conn: Connection, params: Tuple) -> List:
    """Updates an existing file_status record in the database."""
    update_fields, id = params
    set_clause_parts = []
    values = []

    for i, (field, value) in enumerate(update_fields.items()):
        if field == "scan_results":
            set_clause_parts.append(f"{field} = ${i + 1}::jsonb")
        elif field == "status":
            set_clause_parts.append(f"{field} = ${i + 1}::file_status_type")
        else:
            set_clause_parts.append(f"{field} = ${i + 1}") 
        values.append(value)

    values.append(id)
    set_clause = ", ".join(set_clause_parts)

    update_query = f"""
        UPDATE file_status
        SET {set_clause}
        WHERE id = ${len(values)}
        RETURNING id, upload_time, scan_start, scan_end, egress_start, status, scan_results
    """
    try:
        return await conn.fetch(update_query, *values)
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to update file status due to foreign key violation: {e}",exc_info=True)
        raise ValueError("Invalid id provided.") from e
    except DataError as e:
        logger.error(f"Failed to update file_status: invalid data: {e}", exc_info=True)
        raise ValueError(f"Invalid data provided for updating file_status: {e}") from e
    except Exception as e:
        logger.error(f"Error updating file_status: {e}", exc_info=True)
        raise


async def delete_file_status_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes a file_status record from the database by id."""
    delete_query = """
        DELETE FROM file_status
        WHERE id = $1
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting a file_status record: {e}", exc_info=True)
        raise

async def list_file_statuses_from_db(conn: Connection) -> List:
    """Retrieves all file_status records from the database."""
    select_query = """
        SELECT id, upload_time, scan_start, scan_end, egress_start, status, scan_results
        FROM file_status
    """
    try:
        return await conn.fetch(select_query)
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing file_status records: {e}", exc_info=True)
        raise