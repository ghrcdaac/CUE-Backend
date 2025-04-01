from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError, DataError
from typing import Tuple, List, Optional
from uuid import UUID
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def create_file_in_db(conn: Connection, params: Tuple) -> List:
    """Inserts a new file record into the database."""
    insert_query = """
        INSERT INTO file (name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum
    """
    try:
        return await conn.fetchrow(insert_query, *params)
    except UniqueViolationError as e:
        logger.error(f"Failed to create file due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A file with the given attributes already exists.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to create file due to foreign key violation: {e}", exc_info=True)
        raise ValueError("Invalid cueuser_uploaded or collection_id provided.")
    except DataError as e:
        logger.error(f"Failed to create file due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating a file.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating a file: {e}", exc_info=True)
        raise

async def get_file_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves a file record from the database by its ID."""
    select_query = """
        SELECT id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum
        FROM file
        WHERE id = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting a file: {e}", exc_info=True)
        raise

async def get_files_by_name_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves file records from the database by their name."""
    select_query = """
        SELECT id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum
        FROM file
        WHERE name = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred during file lookup by name: {e}", exc_info=True)
        raise

async def update_file_in_db(conn: Connection, params: Tuple) -> List:
    """Updates an existing file record in the database."""
    update_fields, file_id = params
    set_clause = ", ".join([f"{field} = ${i+1}" for i, field in enumerate(update_fields.keys())])
    values = list(update_fields.values())
    values.append(file_id)

    update_query = f"""
        UPDATE file
        SET {set_clause}
        WHERE id = ${len(values)}
        RETURNING id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum
    """
    try:
        return await conn.fetch(update_query, *values)
    except UniqueViolationError as e:
        logger.error(f"Failed to update file due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A file with the given attributes already exists.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to update file due to foreign key violation: {e}", exc_info=True)
        raise ValueError("Invalid cueuser_uploaded or collection_id provided.")
    except DataError as e:
        logger.error(f"Failed to update file due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for updating a file.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating a file: {e}", exc_info=True)
        raise

async def delete_file_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes a file record from the database by its ID."""
    delete_query = """
        DELETE FROM file
        WHERE id = $1
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting a file: {e}", exc_info=True)
        raise

async def list_files_from_db(conn: Connection) -> List:
    """Retrieves all file records from the database."""
    select_query = """
        SELECT id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum
        FROM file
    """
    try:
        return await conn.fetch(select_query)
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing files: {e}", exc_info=True)
        raise