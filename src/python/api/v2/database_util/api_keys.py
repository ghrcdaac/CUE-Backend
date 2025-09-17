from asyncpg import Connection
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

async def store_api_key(
    conn: Connection, key_hash: str, prefix: str, name: str, scopes: List[str],
    user_id: Optional[UUID], created_by_user_id: UUID, proxy_user_name: Optional[str],
    ngroup_id: Optional[UUID], expires_at: datetime, key_display_suffix: str 
) -> UUID:
    """Stores a new hashed API key in the database and returns its ID."""
    query = """
        INSERT INTO api_key (key_hash, prefix, name, scopes, user_id, created_by_user_id, 
                             proxy_user_name, ngroup_id, expires_at, key_display_suffix) 
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) 
        RETURNING id;
    """
    return await conn.fetchval(
        query, key_hash, prefix, name, scopes, user_id, created_by_user_id,
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
        RETURNING user_id, proxy_user_name, ngroup_id, scopes;
    """
    return await conn.fetchrow(query, key_hash)


async def list_api_keys(
    conn: Connection, user_id: UUID, ngroup_id_for_manager: Optional[UUID] = None
) -> List[Dict[str, Any]]:
    """
    Lists API keys with refined privacy rules.
    - Managers see proxy keys for their group and any keys they personally own.
    - Regular users only see keys they personally own.
    - Filters out revoked (soft-deleted) keys.
    """
    base_query = """
        SELECT
            ak.*,
            owner.name AS user_name,
            creator.name AS created_by_user_name
        FROM
            api_key ak
        LEFT JOIN
            cueuser owner ON ak.user_id = owner.id
        LEFT JOIN
            cueuser creator ON ak.created_by_user_id = creator.id
    """
    
    if ngroup_id_for_manager:
        # For managers/admins, show proxy keys for their active group OR any key they own.
        where_clause = """
            WHERE
              (
                (ak.proxy_user_name IS NOT NULL AND ak.ngroup_id = $1)
                OR (ak.user_id = $2)
              )
              AND ak.revoked_at IS NULL
        """
        params = (ngroup_id_for_manager, user_id)
    else:
        # For regular users, only show keys they own.
        where_clause = "WHERE ak.user_id = $1 AND ak.revoked_at IS NULL"
        params = (user_id,)
        
    order_clause = "ORDER BY ak.created_at DESC;"
    query = f"{base_query} {where_clause} {order_clause}"
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