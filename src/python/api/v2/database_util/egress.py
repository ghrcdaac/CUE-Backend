# File: src/python/api/v2/database_util/egress.py

from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError
from typing import List, Optional, Dict, Any
from uuid import UUID
import structlog
import json

logger = structlog.get_logger(__name__)

async def create_egress(conn: Connection, type: str, path: str, config: Dict[str, Any], ngroup_id: UUID) -> Dict[str, Any]:
    """Inserts a new egress record into the database."""
    query = """
        INSERT INTO egress (type, path, config, ngroup_id)
        VALUES ($1, $2, $3::jsonb, $4)
        RETURNING *;
    """
    try:
        config_json = json.dumps(config)
        return await conn.fetchrow(query, type, path, config_json, ngroup_id)
    except ForeignKeyViolationError as e:
        logger.error("db.egress.create.failed_fk", error=str(e))
        raise ValueError(f"Ngroup with ID '{ngroup_id}' not found.") from e

async def get_egress_by_id(conn: Connection, egress_id: UUID) -> Optional[Dict[str, Any]]:
    """Retrieves an egress record from the database by its ID."""
    return await conn.fetchrow("SELECT * FROM egress WHERE id = $1", egress_id)

async def list_egresses(
    conn: Connection,
    requesting_user: Dict[str, Any],
    page_size: int,
    offset: int,
    active_ngroup_id: Optional[UUID] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves all egress records, filtered by the active ngroup and user role.
    """
    logger.info(
        "egress.list.executing_query",
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
        # Admins/Security see all egress targets from all groups.
        if 'admin' in user_roles or 'security' in user_roles:
            where_clause = "" # No filter, show all
        else:
            # All other roles see an empty list if no DAAC is selected.
            # This forces managers to select a DAAC to see its egress targets.
            where_clause = "WHERE FALSE" # Return no rows

    limit_param = len(params) + 1
    offset_param = len(params) + 2

    params.extend([page_size, offset])

    query = f"SELECT * FROM egress {where_clause} ORDER BY type, path LIMIT ${limit_param} OFFSET ${offset_param}"
    return await conn.fetch(query, *params)

async def update_egress(conn: Connection, egress_id: UUID, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Updates an existing egress record in the database."""
    if 'config' in update_data:
        update_data['config'] = json.dumps(update_data['config'])

    fields, values = list(update_data.keys()), list(update_data.values())
    set_clause = ", ".join(f"{field} = ${i+1}" for i, field in enumerate(fields))
    query = f"UPDATE egress SET {set_clause} WHERE id = ${len(fields) + 1} RETURNING *;"
    
    return await conn.fetchrow(query, *values, egress_id)

async def delete_egress(conn: Connection, egress_id: UUID) -> bool:
    """Deletes an egress record from the database by its ID."""
    try:
        # --- Use RETURNING id to robustly check for successful deletion ---
        result = await conn.fetchval("DELETE FROM egress WHERE id = $1 RETURNING id", egress_id)
        # If the result is not None, the deletion was successful.
        return result is not None
    except ForeignKeyViolationError as e:
        logger.warning("db.egress.delete.failed_fk", egress_id=str(egress_id), error=str(e))
        raise ValueError("Cannot delete this egress target because it is still linked to one or more collections.") from e
    
async def get_egress_count(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID] = None) -> int:
    """Retrieves the total Count of egress targets, filtered by ngroup_id"""

    logger.info(
        "egress.count.executing_query",
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
        # Admins/Security see all egress from all groups.
        if 'admin' in user_roles or 'security' in user_roles:
            where_clause = ""  # No filter, show all
        else:
            # All other roles see an empty list if no DAAC is selected.
            # This forces managers to select a DAAC to see its egress.
            where_clause = "WHERE FALSE"  # Return no rows

    try:
        query = f"SELECT count(id) FROM egress {where_clause}"
        total_row = await conn.fetchrow(query,*params)
        total_count = total_row["count"] if total_row else 0
        return total_count
    except Exception as e:
        logger.error(f"Error fetching count: {e}", error=str(e))
        raise ValueError("Cannot fetch total count") from e