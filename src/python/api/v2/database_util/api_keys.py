from asyncpg import Connection
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

async def store_api_key(
    conn: Connection, key_hash: str, prefix: str, name: str, scopes: List[str],
    key_type: str,  # 'personal', 'managed_user', or 'proxy'
    user_id: Optional[UUID], created_by_user_id: UUID, proxy_user_name: Optional[str],
    ngroup_id: Optional[UUID], expires_at: datetime, key_display_suffix: str
) -> UUID:
    """Stores a new hashed API key in the database and returns its ID."""
    query = """
        INSERT INTO api_key (key_hash, prefix, name, scopes, key_type, user_id,
                             created_by_user_id, proxy_user_name, ngroup_id,
                             expires_at, key_display_suffix)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING id;
    """
    return await conn.fetchval(
        query, key_hash, prefix, name, scopes, key_type, user_id, created_by_user_id,
        proxy_user_name, ngroup_id, expires_at, key_display_suffix
    )

async def get_user_from_api_key(conn: Connection, key_hash: str) -> Optional[Dict[str, Any]]:
    """
    Finds an active, non-expired API key and updates its 'last_used_at' timestamp.
    Returns the user ID (if it's a CUE user key) or the ngroup ID (if it's a proxy key).
    """
    query = """
        UPDATE api_key
        SET last_used_at = NOW()
        WHERE key_hash = $1 AND is_active = TRUE AND expires_at > NOW()
        RETURNING user_id, proxy_user_name, ngroup_id, scopes, created_by_user_id;
    """
    return await conn.fetchrow(query, key_hash)


async def list_api_keys(
    conn: Connection,
    requesting_user: Dict[str, Any],
    page_size: int,
    offset: int,
    active_ngroup_id: Optional[UUID] = None
) -> List[Dict[str, Any]]:
    """
    Lists API keys with strict role-based visibility, filtered by the active ngroup.
    """
    base_query = """
        SELECT
            ak.*,
            owner.name AS user_name,
            creator.name AS created_by_user_name
        FROM api_key ak
        LEFT JOIN cueuser owner ON ak.user_id = owner.id
        LEFT JOIN cueuser creator ON ak.created_by_user_id = creator.id
    """

    user_roles = set(requesting_user.get('roles', []))
    params = []
    where_conditions = ["ak.revoked_at IS NULL"]

    # This is the primary filtering logic for when a DAAC is selected in the UI.
    # It applies to ALL users, including admins, enforcing the context.
    if active_ngroup_id:
        where_conditions.append("ak.ngroup_id = $1")
        params.append(active_ngroup_id)
    
    # This is the logic for the default state when NO DAAC is selected.
    else:
        # Admins and Security users see all keys from all groups by default.
        if 'admin' in user_roles or 'security' in user_roles:
            pass  # No additional filter, they see everything.
        else:
            # For any other user (Manager, Staff, etc.), if no DAAC is selected,
            # they see an empty list. This forces a DAAC context to be chosen.
            where_conditions.append("1=0")  # A condition that is always false.
    
    limit_param = len(params) + 1
    offset_param = len(params) + 2

    params.extend([page_size, offset])

    where_clause = f"WHERE {' AND '.join(where_conditions)}"
    order_clause = "ORDER BY ak.created_at DESC"
    query = f"{base_query} {where_clause} {order_clause} LIMIT ${limit_param} OFFSET ${offset_param}"
    
    # Added logging to help debug why the list might be empty.
    logger.info(
        "api_keys.list.executing_query",
        user_roles=list(user_roles),
        active_ngroup_id=str(active_ngroup_id) if active_ngroup_id else None,
        final_where_clause=where_clause
    )

    return await conn.fetch(query, *params)


async def get_api_key_by_id(conn: Connection, key_id: UUID) -> Optional[Dict[str, Any]]:
    """Retrieves a single API key by its ID."""
    return await conn.fetchrow("SELECT * FROM api_key WHERE id = $1", key_id)

async def update_api_key(conn: Connection, key_id: UUID, update_data: Dict[str, Any]) -> bool:
    """Updates an API key (e.g., to set is_active)."""
    fields, values = list(update_data.keys()), list(update_data.values())
    set_clause = ", ".join(f"{field} = ${i+1}" for i, field in enumerate(fields))
    query = f"UPDATE api_key SET {set_clause} WHERE id = ${len(fields) + 1} RETURNING id;"
    
    result = await conn.fetchval(query, *values, key_id)
    return result is not None

async def revoke_api_key(conn: Connection, key_id: UUID) -> bool:
    """Deletes an API key."""
    result = await conn.execute("DELETE FROM api_key WHERE id = $1", key_id)
    return result.strip() == "DELETE 1"

async def soft_delete_api_key(conn: Connection, key_id: UUID) -> bool:
    """Soft-deletes an API key by setting the revoked_at timestamp and deactivating it."""
    query = "UPDATE api_key SET is_active = FALSE, revoked_at = NOW() WHERE id = $1 RETURNING id;"
    result = await conn.fetchval(query, key_id)
    return result is not None

# --- Function to update last_used_at ---
async def record_key_usage(conn: Connection, key_id: UUID) -> bool:
    """Updates the last_used_at timestamp for a given key."""
    query = "UPDATE api_key SET last_used_at = NOW() WHERE id = $1 RETURNING id;"
    result = await conn.fetchval(query, key_id)
    return result is not None

async def count_api_keys(
    conn: Connection,
    requesting_user: Dict[str, Any],
    active_ngroup_id: Optional[UUID] = None
) -> int:
    """
    Returns the total number of API keys matching the same filters used
    in list_api_keys(), for pagination support.
    """
    user_roles = set(requesting_user.get('roles', []))
    params = []
    where_conditions = ["ak.revoked_at IS NULL"]

    if active_ngroup_id:
        where_conditions.append("ak.ngroup_id = $1")
        params.append(active_ngroup_id)
    else:
        if 'admin' in user_roles or 'security' in user_roles:
            pass 
        else:
            where_conditions.append("1=0") 

    where_clause = f"WHERE {' AND '.join(where_conditions)}"

    count_query = f"""
        SELECT COUNT(*)
        FROM api_key ak
        {where_clause};
    """

    logger.info(
        "api_keys.count.executing_query",
        user_roles=list(user_roles),
        active_ngroup_id=str(active_ngroup_id) if active_ngroup_id else None,
        final_where_clause=where_clause
    )

    result = await conn.fetchval(count_query, *params)
    return result if result else 0
