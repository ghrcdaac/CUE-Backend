# ==============================================================================
# File: src/python/api/v2/database_util/api_keys.py (New)
# Purpose: Contains all raw SQL queries for API key management.
# ==============================================================================
from asyncpg import Connection
from typing import List, Dict, Any, Optional
from uuid import UUID
import structlog

logger = structlog.get_logger(__name__)

async def store_api_key(conn: Connection, key_hash: str, prefix: str, user_id: UUID, name: str, scopes: List[str]) -> UUID:
    """Stores a new hashed API key in the database and returns its ID."""
    query = """
        INSERT INTO api_key (key_hash, prefix, user_id, name, scopes)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id;
    """
    key_id = await conn.fetchval(query, key_hash, prefix, user_id, name, scopes)
    logger.info("db.api_key.created", key_id=str(key_id), user_id=str(user_id))
    return key_id

async def get_user_from_api_key(conn: Connection, key_hash: str) -> Optional[Dict[str, Any]]:
    """
    Finds an active API key by its hash and returns the associated user ID and key details.
    Also updates the 'last_used_at' timestamp.
    """
    query = """
        UPDATE api_key
        SET last_used_at = NOW()
        WHERE key_hash = $1 AND is_active = TRUE
        RETURNING id, user_id, scopes;
    """
    return await conn.fetchrow(query, key_hash)

async def list_api_keys_for_user(conn: Connection, user_id: UUID) -> List[Dict[str, Any]]:
    """Lists all non-secret information about API keys for a specific user."""
    query = """
        SELECT id, name, prefix, scopes, created_at, last_used_at, is_active
        FROM api_key
        WHERE user_id = $1
        ORDER BY created_at DESC;
    """
    return await conn.fetch(query, user_id)

async def revoke_api_key(conn: Connection, key_id: UUID, user_id: UUID) -> bool:
    """Deletes an API key, ensuring the user owns it."""
    query = """
        DELETE FROM api_key
        WHERE id = $1 AND user_id = $2
        RETURNING id;
    """
    result = await conn.execute(query, key_id, user_id)
    deleted_count = int(result.split(" ")[1])
    if deleted_count > 0:
        logger.info("db.api_key.revoked", key_id=str(key_id), user_id=str(user_id))
        return True
    return False
