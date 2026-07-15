# File: src/python/api/v2/database_util/provider.py (Updated)

from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError
from typing import List, Optional, Dict, Any
from uuid import UUID
import structlog

logger = structlog.get_logger(__name__)

async def create_provider(conn: Connection, ngroup_id: UUID, short_name: str, long_name: str, can_upload: bool, point_of_contact: UUID, reason: str) -> Dict[str, Any]:
    """Inserts a new provider record into the database."""
    query = """
        INSERT INTO provider (ngroup_id, short_name, long_name, can_upload, point_of_contact, reason)
        VALUES ($1, $2, $3, $4, $5,$6)
        RETURNING *;
    """
    try:
        return await conn.fetchrow(query, ngroup_id, short_name, long_name, can_upload, point_of_contact,reason)
    except UniqueViolationError as e:
        logger.error("db.provider.create.failed_unique", error=str(e))
        raise ValueError("A provider with the same short_name or long_name already exists.") from e
    except ForeignKeyViolationError as e:
        logger.error("db.provider.create.failed_fk", error=str(e))
        raise ValueError("The specified ngroup_id or point_of_contact does not exist.") from e

async def get_provider_by_id(conn: Connection, provider_id: UUID) -> Optional[Dict[str, Any]]:
    """Retrieves a provider record from the database by its ID."""
    return await conn.fetchrow("SELECT * FROM provider WHERE id = $1", provider_id)

async def list_providers(
    conn: Connection,
    requesting_user: Dict[str, Any],
    page_size: int,
    offset: int,
    can_upload: bool,
    active_ngroup_id: Optional[UUID] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves all provider records, filtered by the active ngroup and user role.
    """
    logger.info(
        "provider.list.executing_query",
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
    
    can_upload_param = len(params) + 1
    if can_upload is not None:
        #test where class with empty string
        if where_clause:
            where_clause = f"{where_clause} AND can_upload = ${can_upload_param}"
            params.append(can_upload)
        
        else:
            where_clause = f"WHERE can_upload = ${can_upload_param}"
            params.append(can_upload)
    
    limit_param = len(params) + 1
    offset_param = len(params) + 2

    params.extend([page_size, offset])

    query = f"""
        SELECT
            p.*,
            jsonb_build_object(
                'id', u.id,
                'name', u.name
            ) AS point_of_contact
        FROM provider p
        LEFT JOIN cueuser u ON p.point_of_contact = u.id
        {where_clause}
        ORDER BY p.short_name
        LIMIT ${limit_param}
        OFFSET ${offset_param}
    """
    return await conn.fetch(query, *params)

async def list_providers_for_form(conn: Connection, ngroup_id: UUID) -> List[Dict[str, Any]]:
    """Retrieves a simplified list of providers (id, short_name) for a given ngroup."""
    return await conn.fetch("SELECT id, short_name FROM provider WHERE ngroup_id = $1 ORDER BY short_name", ngroup_id)

async def update_provider(conn: Connection, provider_id: UUID, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Updates an existing provider record in the database."""
    fields, values = list(update_data.keys()), list(update_data.values())
    set_clause = ", ".join(f"{field} = ${i+1}" for i, field in enumerate(fields))
    query = f"UPDATE provider SET {set_clause} WHERE id = ${len(fields) + 1} RETURNING *;"
    
    try:
        return await conn.fetchrow(query, *values, provider_id)
    except UniqueViolationError as e:
        logger.error("db.provider.update.failed_unique", error=str(e))
        raise ValueError("A provider with the same short_name or long_name already exists.") from e
    except ForeignKeyViolationError as e:
        logger.error("db.provider.update.failed_fk", error=str(e))
        raise ValueError("The specified point_of_contact does not exist.") from e


async def delete_provider(conn: Connection, provider_id: UUID) -> bool:
    """Deletes a provider record from the database by its ID."""
    try:
        result = await conn.execute("DELETE FROM provider WHERE id = $1", provider_id)
        return result.strip() == "DELETE 1"
    except ForeignKeyViolationError as e:
        logger.warning("db.provider.delete.failed_fk", provider_id=str(provider_id), error=str(e))
        raise ValueError("Cannot delete this provider because it is still linked to one or more collections.") from e
    
async def get_providers_count(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: int, can_upload: bool) -> int:
    "Retrives the total Count of the providers, filtered by ngroup_id"

    logger.info(
        "provider.count.executing_query",
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
    
    can_upload_param = len(params) + 1
    if can_upload is not None:
        #test where class with empty string
        if where_clause:
            where_clause = f"{where_clause} AND can_upload = ${can_upload_param}"
            params.append(can_upload)
        
        else:
            where_clause = f"where can_upload = ${can_upload_param}"
            params.append(can_upload)

    try:
        query = f"SELECT count(id) FROM provider {where_clause}"
        total_row = await conn.fetchrow(query,*params)
        total_count = total_row["count"] if total_row else 0
        return total_count
    except Exception as e:
        logger.error(f"Error fetching count: {e}", error=str(e))
        raise ValueError("Cannot fetch total count") from e