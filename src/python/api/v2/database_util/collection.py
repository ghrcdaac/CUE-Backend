# File: src/python/api/v2/database_util/collection.py

from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import structlog

logger = structlog.get_logger(__name__)

async def create_collection(conn: Connection, short_name: str, active: bool, ngroup_id: UUID, provider_id: UUID, egress_id: UUID) -> Dict[str, Any]:
    """Inserts a new collection record into the database."""
    query = """
        INSERT INTO collection (short_name, active, ngroup_id, provider_id, egress_id)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *;
    """
    try:
        return await conn.fetchrow(query, short_name, active, ngroup_id, provider_id, egress_id)
    except UniqueViolationError as e:
        logger.error("db.collection.create.failed_unique", error=str(e))
        raise ValueError(f"A collection with short_name '{short_name}' already exists.") from e
    except ForeignKeyViolationError as e:
        logger.error("db.collection.create.failed_fk", error=str(e))
        raise ValueError("The specified ngroup_id, provider_id, or egress_id does not exist.") from e

async def get_collection_by_id(conn: Connection, collection_id: UUID) -> Optional[Dict[str, Any]]:
    """Retrieves a collection record from the database by its ID."""
    return await conn.fetchrow("SELECT * FROM collection WHERE id = $1", collection_id)

async def get_collection_by_short_name(conn: Connection, short_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves a collection record from the database by its short_name."""
    return await conn.fetchrow("SELECT * FROM collection WHERE short_name = $1", short_name)


async def list_collections_by_ngroup(conn: Connection, params: Tuple) -> List[Dict[str, Any]]:
    """Retrieves all collection records for a specific ngroup."""
    select_query = """
        SELECT id, ngroup_id, egress_id, short_name, provider_id, active
        FROM collection
        WHERE ngroup_id = $1  -- Filter by ngroup_id
        ORDER BY short_name asc
        LIMIT $2 OFFSET $3
    """
    return await conn.fetch(select_query, *params)

async def update_collection(conn: Connection, collection_id: UUID, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Updates an existing collection record in the database."""
    fields, values = list(update_data.keys()), list(update_data.values())
    set_clause = ", ".join(f"{field} = ${i+1}" for i, field in enumerate(fields))
    query = f"UPDATE collection SET {set_clause} WHERE id = ${len(fields) + 1} RETURNING *;"
    
    try:
        return await conn.fetchrow(query, *values, collection_id)
    except UniqueViolationError as e:
        logger.error("db.collection.update.failed_unique", error=str(e))
        raise ValueError("A collection with the same short_name already exists.") from e
    except ForeignKeyViolationError as e:
        logger.error("db.collection.update.failed_fk", error=str(e))
        raise ValueError("The specified provider_id or egress_id does not exist.") from e

async def delete_collection(conn: Connection, collection_id: UUID) -> bool:
    """Deletes a collection record from the database by its ID."""
    try:
        result = await conn.execute("DELETE FROM collection WHERE id = $1", collection_id)
        return result.strip() == "DELETE 1"
    except ForeignKeyViolationError as e:
        logger.warning("db.collection.delete.failed_fk", collection_id=str(collection_id), error=str(e))
        raise ValueError("Cannot delete this collection because it is still linked to one or more files.") from e
    
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