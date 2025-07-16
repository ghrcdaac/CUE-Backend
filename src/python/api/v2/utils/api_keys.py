# ==============================================================================
# File: src/python/api/v2/utils/api_keys.py (New)
# Purpose: Contains the business logic for generating and managing API keys.
# ==============================================================================
import secrets
import hashlib
from uuid import UUID
from typing import Dict, Any, List

import structlog

from core.db import get_db_connection
from ..database_util import api_keys as api_key_db
from ..type_util.api_keys import ApiKeyInfo

logger = structlog.get_logger(__name__)

class ApiKeyNotFoundError(Exception):
    pass

def _generate_secure_key() -> (str, str):
    """Generates a secure, random API key and its prefix."""
    prefix = "cue_sk_"
    secret_part = secrets.token_urlsafe(32)
    return f"{prefix}{secret_part}", prefix

def _hash_key(key: str) -> str:
    """Hashes the API key using SHA-256 for secure storage."""
    return hashlib.sha256(key.encode()).hexdigest()

async def create_api_key_for_user(user_id: UUID, name: str) -> Dict[str, Any]:
    """
    Generates a new API key, stores its hash, and returns the raw key.
    The raw key is never stored and is only returned once upon creation.
    """
    raw_key, prefix = _generate_secure_key()
    key_hash = _hash_key(raw_key)
    
    # For now, all keys have a fixed scope. This could be parameterized in the future.
    scopes = ["file:upload"]

    async with get_db_connection() as conn:
        key_id = await api_key_db.store_api_key(conn, key_hash, prefix, user_id, name, scopes)

    logger.info("api_key.created", user_id=str(user_id), key_id=str(key_id))
    return {
        "id": key_id,
        "name": name,
        "key": raw_key
    }

async def list_user_api_keys(user_id: UUID) -> List[ApiKeyInfo]:
    """Retrieves a list of all API keys for a user."""
    async with get_db_connection() as conn:
        keys_data = await api_key_db.list_api_keys_for_user(conn, user_id)
    return [ApiKeyInfo.model_validate(key) for key in keys_data]

async def revoke_user_api_key(key_id: UUID, user_id: UUID):
    """Revokes an API key, ensuring the user is the owner."""
    async with get_db_connection() as conn:
        success = await api_key_db.revoke_api_key(conn, key_id, user_id)
    
    if not success:
        raise ApiKeyNotFoundError("API Key not found or user does not have permission to revoke it.")
