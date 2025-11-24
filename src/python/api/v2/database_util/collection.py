# File: src/python/api/v2/database_util/collection.py

from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError
from typing import List, Optional, Dict, Any
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


async def list_collections(
    conn: Connection,
    requesting_user: Dict[str, Any],
    page_size: int,
    offset: int,
    active_ngroup_id: Optional[UUID] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves all collection records, filtered by the active ngroup and user role.
    """
    logger.info(
        "collection.list.executing_query",
        user_roles=requesting_user.get('roles', []),
        active_ngroup_id=str(active_ngroup_id) if active_ngroup_id else None
    )
    
    user_roles = set(requesting_user.get('roles', []))
    params = []
    
    # If a DAAC is selected, ALL roles are strictly filtered by it.
    if active_ngroup_id:
        where_clause = "WHERE ngroup_id = $1"
        params.append(active_ngroup_id)
    else:
        # If NO DAAC is selected:
        # Admins/Security see all collections from all groups.
        if 'admin' in user_roles or 'security' in user_roles:
            where_clause = "" # No filter, show all
        else:
            # All other roles see an empty list if no DAAC is selected.
            # This forces managers to select a DAAC to see its collections.
            where_clause = "WHERE FALSE" # Return no rows

    limit_param = len(params) + 1
    offset_param = len(params) + 2

    params.extend([page_size, offset])

    query = f"SELECT * FROM collection {where_clause} ORDER BY short_name LIMIT ${limit_param} OFFSET ${offset_param}"
    return await conn.fetch(query, *params)

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

async def get_collection_count(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: int) -> int:
    "Retrives the total Count of the collection, filtered by ngroup_id"

    logger.info(
        "collection.count.executing_query",
        user_roles=requesting_user.get('roles', []),
        active_ngroup_id=str(active_ngroup_id) if active_ngroup_id else None
    )

    user_roles = set(requesting_user.get('roles', []))
    params = []

    # If a DAAC is selected, ALL roles are strictly filtered by it.
    if active_ngroup_id:
        where_clause = "WHERE ngroup_id = $1"
        params.append(active_ngroup_id)
    else:
        # If NO DAAC is selected:
        # Admins/Security see all providers from all groups.
        if 'admin' in user_roles or 'security' in user_roles:
            where_clause = ""  # No filter, show all
        else:
            # All other roles see an empty list if no DAAC is selected.
            # This forces managers to select a DAAC to see its providers.
            where_clause = "WHERE FALSE"  # Return no rows

    try:
        query = f"SELECT count(id) FROM collection {where_clause}"
        total_row = await conn.fetchrow(query, *params)
        total_count = total_row["count"] if total_row else 0
        return total_count
    except Exception as e:
        logger.error(f"Error fetching count: {e}", error=str(e))
        raise ValueError("Cannot fetch total count") from e