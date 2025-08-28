from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError, DataError
from typing import Tuple, List, Optional, Dict, Any
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

# --- Helper to get ngroup_id for a file ---
async def get_ngroup_id_for_file_db(conn: Connection, file_id: UUID) -> Optional[UUID]:
    """Retrieves the ngroup_id associated with a file via its collection."""
    query = """
        SELECT c.ngroup_id
        FROM file f
        JOIN collection c ON f.collection_id = c.id
        WHERE f.id = $1
    """
    try:
        return await conn.fetchval(query, file_id)
    except Exception as e:
        logger.error(f"Error fetching ngroup_id for file {file_id}: {e}", exc_info=True)
        raise 

# --- CRUD Functions ---
async def create_file_in_db(conn: Connection, params: Tuple) -> List:
    """Inserts a new file record into the database."""
    insert_query = """
        INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, collection_path, edpub, checksum)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id, name, type, cueuser_uploaded, size_bytes, collection_id, collection_path, edpub, checksum 
    """
    try:
        return await conn.fetchrow(insert_query, *params)
    except UniqueViolationError as e:
        logger.error(f"Failed to create file due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A file with the given attributes already exists.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to create file due to foreign key violation: {e}", exc_info=True)
        
        if "file_cueuser_uploaded_fkey" in str(e):
             raise ValueError(f"Invalid cueuser_uploaded ID provided: {params[2]}")
        elif "file_collection_id_fkey" in str(e):
             raise ValueError(f"Invalid collection_id provided: {params[4]}")
        else:
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

async def get_files_by_name_from_db(conn: Connection, file_name: str, ngroup_id: UUID) -> List:
    """Retrieves file records from the database by name, filtered by ngroup."""
    select_query = """
        SELECT f.id, f.name, f.type, f.cueuser_uploaded, f.size_bytes, f.collection_id, f.edpub, f.checksum
        FROM file f
        JOIN collection c ON f.collection_id = c.id
        WHERE f.name = $1 AND c.ngroup_id = $2
    """
    try:
        return await conn.fetch(select_query, file_name, ngroup_id)
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
        raise ValueError("Update resulted in a duplicate constraint violation.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to update file due to foreign key violation: {e}", exc_info=True)
        raise ValueError("Invalid cueuser_uploaded or collection_id provided in update.")
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
        # Consider ForeignKeyViolationError if files cannot be deleted due to references
        logger.error(f"An unexpected error occurred while deleting a file: {e}", exc_info=True)
        raise

async def list_files_from_db(conn: Connection, ngroup_id: UUID) -> List:
    """Retrieves all file records for a specific ngroup."""
    select_query = """
        SELECT f.id, f.name, f.type, f.cueuser_uploaded, f.size_bytes, f.collection_id, f.edpub, f.checksum
        FROM file f
        JOIN collection c ON f.collection_id = c.id
        WHERE c.ngroup_id = $1
        ORDER BY f.name -- Example ordering
    """
    try:
        return await conn.fetch(select_query, ngroup_id)
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing files: {e}", exc_info=True)
        raise
