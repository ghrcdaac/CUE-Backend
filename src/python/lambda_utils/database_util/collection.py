# lambda_utils/database_util/collection.py
from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError, DataError
from typing import Tuple, List, Optional, Any
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
        logger.error(f"Failed to create collection: {e}", exc_info=True)
        raise ValueError("Unique constraint violation.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to create collection: {e}", exc_info=True)
        raise ValueError("Foreign key violation.")
    except DataError as e:
        logger.error(f"Failed to create collection: {e}", exc_info=True)
        raise ValueError("Invalid data.")
    except Exception as e:
        logger.error(f"Failed to create collection: {e}", exc_info=True)
        raise

async def get_collection_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves a collection record from the database by its ID, filtered by ngroup_id."""
    select_query = """
        SELECT id, ngroup_id, egress_id, short_name, provider_id, active
        FROM collection
        WHERE id = $1 AND ngroup_id = $2  -- Filter by ID and ngroup_id
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"Error getting collection: {e}", exc_info=True)
        raise

async def get_collection_by_lookup_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves a collection record by short_name, filtered by ngroup_id."""
    select_query = """
        SELECT id, ngroup_id, egress_id, short_name, provider_id, active
        FROM collection
        WHERE short_name = $1 AND ngroup_id = $2  -- Filter by short_name and ngroup_id
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"Error during collection lookup: {e}", exc_info=True)
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
        logger.error(f"Failed to update collection: {e}", exc_info=True)
        raise ValueError("Unique constraint violation.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to update collection: {e}", exc_info=True)
        raise ValueError("Foreign key violation.")
    except DataError as e:
        logger.error(f"Failed to update collection: {e}", exc_info=True)
        raise ValueError("Invalid data.")
    except Exception as e:
        logger.error(f"Failed to update collection: {e}", exc_info=True)
        raise


async def delete_collection_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes a collection record by its ID, filtered by ngroup_id."""
    delete_query = """
        DELETE FROM collection
        WHERE id = $1 AND ngroup_id = $2  -- Filter by ID and ngroup_id
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"Error deleting collection: {e}", exc_info=True)
        raise

async def list_collections_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves all collection records, filtered by ngroup_id."""
    select_query = """
        SELECT id, ngroup_id, egress_id, short_name, provider_id, active
        FROM collection
        WHERE ngroup_id = $1
        ORDER BY short_name asc
        LIMIT $2 OFFSET $3
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"Error listing collections: {e}", exc_info=True)
        raise

async def list_files_for_collection_from_db(conn: Connection, params: Tuple) -> List:
    """Lists files for a collection, filtered by ngroup_id, with pagination."""
    collection_id, ngroup_id, limit, offset = params
    select_query = """
        SELECT f.id, f.name, f.type, f.cueuser_uploaded, f.size_bytes, f.collection_id, f.edpub, f.checksum
        FROM file f
        JOIN collection c ON f.collection_id = c.id
        WHERE c.id = $1 AND c.ngroup_id = $2  -- Filter by collection_id and ngroup_id
        LIMIT $3 OFFSET $4
    """
    try:
        return await conn.fetch(select_query, collection_id, ngroup_id, limit, offset)
    except Exception as e:
        logger.error(f"Error listing files: {e}", exc_info=True)
        raise

async def count_files_for_collection_from_db(conn: Connection, params: Tuple) -> int:
    """Counts files for a collection, filtered by ngroup_id."""
    collection_id, ngroup_id = params  # Expect ngroup_id as well
    count_query = """
    SELECT COUNT(*) as count
    FROM file f
    JOIN collection c ON f.collection_id = c.id
    WHERE c.id = $1 AND c.ngroup_id = $2  -- Filter by collection_id and ngroup_id
"""
    try:
        result = await conn.fetchrow(count_query, *params)
        return result['count'] if result else 0
    except Exception as e:
        logger.error(f"An unexpected error occurred while counting files for collection: {e}", exc_info=True)
        raise

async def get_collection_files_count(conn: Connection, params: Tuple) -> List:
    """Retrieves a collection files count with pagination."""
    select_query = """
        SELECT count(f.id) AS file_count, 
               f.collection_id, 
               c.ngroup_id, 
               c.short_name
        FROM file f 
        JOIN collection c ON f.collection_id = c.id
        WHERE c.ngroup_id = $1
        GROUP BY f.collection_id, c.ngroup_id, c.short_name
        ORDER BY c.short_name asc
        LIMIT $2 OFFSET $3
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"Error during collection lookup: {e}", exc_info=True)
        raise

async def get_collection_total_count_by_files(conn: Connection, params: Tuple):
    total_query = """
        SELECT COUNT(DISTINCT f.collection_id) AS total_count
        FROM file f 
        JOIN collection c ON f.collection_id = c.id
        WHERE c.ngroup_id = $1
    """
    try:
        total_row = await conn.fetchrow(total_query, params)
        total_count = total_row["total_count"] if total_row else 0
        return total_count
    except Exception as e:
        logger.error(f"Error during collection lookup: {e}", exc_info=True)
        raise

async def get_collection_count(conn: Connection, params: Tuple) -> int:
    "Retrives the total Count of the collections, filtered by ngroup_id"
    total_query = """
        SELECT count(id) as total_count
        FROM collection
        WHERE ngroup_id = $1
    """
    try:
        total_row = await conn.fetchrow(total_query, params)
        total_count = total_row["total_count"] if total_row else 0
        return total_count
    except Exception as e:
        logger.error(f"Error fetching count: {e}", exc_info=True)
        raise