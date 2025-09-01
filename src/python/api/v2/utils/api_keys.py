import secrets
import hashlib
from uuid import UUID
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
import structlog

from core.db import get_db_connection
from v2.database_util import api_keys as api_key_db
from v2.database_util import cueuser as user_db # Needed for validation
from v2.type_util.api_keys import ApiKeyInfo, ApiKeyCreateRequest, ApiKeyUpdateRequest
from v2.type_util.auth import AuthUser

logger = structlog.get_logger(__name__)

class ApiKeyNotFoundError(Exception): pass
class ApiKeyPermissionError(Exception): pass

def _generate_secure_key() -> (str, str):
    """Generates a secure, random API key and its prefix."""
    prefix = "cue_sk_"
    secret_part = secrets.token_urlsafe(32)
    return f"{prefix}{secret_part}", prefix

def _hash_key(key: str) -> str:
    """Hashes the API key using SHA-256 for secure storage."""
    return hashlib.sha256(key.encode()).hexdigest()

async def create_api_key(request: ApiKeyCreateRequest, creator: AuthUser) -> Dict[str, Any]:
    """Orchestrates the creation of a new API key with permission checks."""
    user_id_to_assign = request.target_user_id
    proxy_name = request.proxy_user_name
    ngroup_id_for_proxy = request.ngroup_id

    # A regular user can only create keys for themselves
    if "admin" not in creator.roles and "daac_manager" not in creator.roles and "daac_staff" not in creator.roles:
        if user_id_to_assign and user_id_to_assign != creator.id:
            raise ApiKeyPermissionError("You can only create API keys for yourself.")
        if proxy_name:
            raise ApiKeyPermissionError("You cannot create proxy keys.")
        user_id_to_assign = creator.id # Default to self

    async with get_db_connection() as conn:
        # If creating for a CUE user, validate that user exists and the creator has access to them
        if user_id_to_assign:
            target_user = await user_db.get_user_by_id(conn, user_id_to_assign)
            if not target_user:
                raise ValueError("Target user not found.")
            target_user_ngroups = {str(ng['id']) for ng in target_user.get('ngroups', [])}
            if "admin" not in creator.roles and not set(creator.ngroups).intersection(target_user_ngroups):
                raise ApiKeyPermissionError("You do not have permission to create a key for this user.")
        
        # If creating a proxy key, validate the creator has access to the ngroup
        elif ngroup_id_for_proxy:
            if "admin" not in creator.roles and str(ngroup_id_for_proxy) not in creator.ngroups:
                raise ApiKeyPermissionError("You do not have permission to create a key for this ngroup.")

    raw_key, prefix = _generate_secure_key()
    key_hash = _hash_key(raw_key)
    expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)

    async with get_db_connection() as conn:
        key_id = await api_key_db.store_api_key(
            conn, key_hash, prefix, request.name, request.scopes, user_id_to_assign,
            creator.id, proxy_name, ngroup_id_for_proxy, expires_at
        )

    logger.info("api_key.created", key_id=str(key_id), creator_id=str(creator.id))
    return {"id": key_id, "name": request.name, "key": raw_key}

async def list_api_keys(user: AuthUser) -> List[ApiKeyInfo]:
    """Retrieves API keys based on the user's role and active ngroup."""
    ngroup_filter = None
    if "admin" in user.roles or "daac_manager" in user.roles or "daac_staff" in user.roles:
        if user.active_ngroup_id:
            ngroup_filter = UUID(user.active_ngroup_id)

    async with get_db_connection() as conn:
        keys_data = await api_key_db.list_api_keys(conn, user.id, ngroup_filter)
    
    return [ApiKeyInfo.model_validate(dict(key)) for key in keys_data]

async def update_api_key(key_id: UUID, update_request: ApiKeyUpdateRequest, user: AuthUser):
    """Updates an API key's status after checking permissions."""
    async with get_db_connection() as conn:
        key_to_update = await api_key_db.get_api_key_by_id(conn, key_id)
        if not key_to_update:
            raise ApiKeyNotFoundError("API Key not found.")

        # Check permissions
        can_manage = False
        if key_to_update['created_by_user_id'] == user.id:
            can_manage = True
        elif "admin" in user.roles or "daac_manager" in user.roles or "daac_staff" in user.roles:
            # Check if key belongs to a user in the manager's group
            if key_to_update['user_id']:
                target_user = await user_db.get_user_by_id(conn, key_to_update['user_id'])
                target_user_ngroups = {str(ng['id']) for ng in target_user.get('ngroups', [])}
                if set(user.ngroups).intersection(target_user_ngroups):
                    can_manage = True
            # Check if key is a proxy key in the manager's group
            elif key_to_update['ngroup_id'] and str(key_to_update['ngroup_id']) in user.ngroups:
                can_manage = True

        if not can_manage:
            raise ApiKeyPermissionError("You do not have permission to update this key.")

        await api_key_db.update_api_key(conn, key_id, update_request.model_dump())
    logger.info("api_key.updated", key_id=str(key_id), updater_id=str(user.id))

async def revoke_api_key(key_id: UUID, user: AuthUser):
    """Revokes an API key after checking permissions."""
    # The permission check logic is identical to update, so we can reuse it
    await update_api_key(key_id, ApiKeyUpdateRequest(is_active=False), user) # First, ensure it's inactive
    
    async with get_db_connection() as conn:
        success = await api_key_db.revoke_api_key(conn, key_id)
    if not success:
        raise ApiKeyNotFoundError("API Key not found.")
    logger.info("api_key.revoked", key_id=str(key_id), revoker_id=str(user.id))
