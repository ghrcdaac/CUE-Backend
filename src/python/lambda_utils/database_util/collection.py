from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError, DataError
from typing import Tuple, List, Optional
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

async def create_collection_in_db(conn: Connection, params: Tuple) -> List:
    """Inserts a new collection record into the database."""
    insert_query = """
        INSERT INTO collection (ngroup_id, egress_id, short_name, provider_id, active)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, ngroup_id, egress_id, short_name, provider_id, active
    """
    try:
        return await conn.fetch(insert_query, *params)
    except UniqueViolationError as e:
        logger.error(f"Failed to create collection due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A collection with the given short_name already exists.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to create collection due to foreign key violation: {e}", exc_info=True)
        raise ValueError("Invalid ngroup_id, egress_id, or provider_id provided.")
    except DataError as e:
        logger.error(f"Failed to create collection due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating a collection.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating a collection: {e}", exc_info=True)
        raise

async def get_collection_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves a collection record from the database by its ID."""
    select_query = """
        SELECT id, ngroup_id, egress_id, short_name, provider_id, active
        FROM collection
        WHERE id = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting a collection: {e}", exc_info=True)
        raise

async def get_collection_by_lookup_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves a collection record from the database by short_name."""
    select_query = """
        SELECT id, ngroup_id, egress_id, short_name, provider_id, active
        FROM collection
        WHERE short_name = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred during collection lookup: {e}", exc_info=True)
        raise

async def update_collection_in_db(conn: Connection, params: Tuple) -> List:
    """Updates an existing collection record in the database."""
    update_fields, collection_id = params
    set_clause = ", ".join([f"{field} = ${i+1}" for i, field in enumerate(update_fields.keys())])
    values = list(update_fields.values())
    values.append(collection_id)

    update_query = f"""
        UPDATE collection
        SET {set_clause}
        WHERE id = ${len(values)}
        RETURNING id, ngroup_id, egress_id, short_name, provider_id, active
    """
    try:
        return await conn.fetch(update_query, *values)
    except UniqueViolationError as e:
        logger.error(f"Failed to update collection due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A collection with the given short_name already exists.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to update collection due to foreign key violation: {e}", exc_info=True)
        raise ValueError("Invalid ngroup_id, egress_id, or provider_id provided.")
    except DataError as e:
        logger.error(f"Failed to update collection due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for updating a collection.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating a collection: {e}", exc_info=True)
        raise

async def delete_collection_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes a collection record from the database by its ID."""
    delete_query = """
        DELETE FROM collection
        WHERE id = $1
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting a collection: {e}", exc_info=True)
        raise

async def list_collections_from_db(conn: Connection) -> List:
    """Retrieves all collection records from the database."""
    select_query = """
        SELECT id, ngroup_id, egress_id, short_name, provider_id, active
        FROM collection
    """
    try:
        return await conn.fetch(select_query)
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing collections: {e}", exc_info=True)
        raise

async def list_files_for_collection_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves all files associated with a collection from the database with pagination."""
    collection_id, limit, offset = params
    select_query = """
        SELECT id, name, type, cueuser_uploaded, size_bytes, collection_id, edpub, checksum
        FROM file
        WHERE collection_id = $1
        LIMIT $2 OFFSET $3
    """
    try:
        return await conn.fetch(select_query, collection_id, limit, offset)
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing files for collection: {e}", exc_info=True)
        raise

async def count_files_for_collection_from_db(conn: Connection, params: Tuple) -> int:
    """Counts the total number of files associated with a collection."""
    count_query = """
        SELECT COUNT(*) as count
        FROM file
        WHERE collection_id = $1
    """
    try:
        result = await conn.fetchrow(count_query, *params)
        return result['count'] if result else 0
    except Exception as e:
        logger.error(f"An unexpected error occurred while counting files for collection: {e}", exc_info=True)
        raise