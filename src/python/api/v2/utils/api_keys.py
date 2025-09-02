# v2/utils/api_keys.py

import secrets
import hashlib
from uuid import UUID
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
import structlog

from core.db import get_db_connection
from v2.database_util import api_keys as api_key_db
from v2.database_util import cueuser as user_db
from v2.type_util.api_keys import ApiKeyInfo, ApiKeyCreateRequest, ApiKeyUpdateRequest
from v2.type_util.auth import AuthUser

logger = structlog.get_logger(__name__)

class ApiKeyNotFoundError(Exception): pass
class ApiKeyPermissionError(Exception): pass

# --- INTERNAL HELPER FUNCTIONS (UNCHANGED) ---
def _generate_secure_key() -> (str, str):
    """Generates a secure, random API key and its prefix."""
    prefix = "cue_sk_"
    secret_part = secrets.token_urlsafe(32)
    return f"{prefix}{secret_part}", prefix

def _hash_key(key: str) -> str:
    """Hashes the API key using SHA-256 for secure storage."""
    return hashlib.sha256(key.encode()).hexdigest()

# --- NEW: Helper function to robustly check permissions ---
async def _can_manager_access_key(manager: AuthUser, key_info: Dict[str, Any], conn) -> bool:
    """Checks if a manager has permission to access a given key."""
    if "admin" in manager.roles:
        return True
    
    # Check if key is a proxy key within one of the manager's groups
    if key_info['proxy_user_name'] and key_info['ngroup_id']:
        if str(key_info['ngroup_id']) in manager.ngroups:
            return True

    # Check if key belongs to a user within one of the manager's groups
    if key_info['user_id']:
        target_user = await user_db.get_user_by_id(conn, key_info['user_id'])
        if not target_user:
            return False
        
        # --- This block handles both list-of-strings and list-of-dicts for ngroups ---
        target_ngroups_raw = target_user.get('ngroups', [])
        target_user_ngroups = set()
        for ng in target_ngroups_raw:
            if isinstance(ng, dict):
                ng_id = ng.get('id')
                if ng_id:
                    target_user_ngroups.add(str(ng_id))
            else:
                target_user_ngroups.add(str(ng))
       
        
        if set(manager.ngroups).intersection(target_user_ngroups):
            return True
            
    return False


async def create_api_key(request: ApiKeyCreateRequest, creator: AuthUser) -> Dict[str, Any]:
    """Orchestrates the creation of a new API key with permission checks."""
    user_id_to_assign = request.target_user_id
    proxy_name = request.proxy_user_name
    ngroup_id_for_proxy = request.ngroup_id
    
    # A regular user can only create keys for themselves
    is_manager_role = any(role in creator.roles for role in ["admin", "daac_manager", "daac_staff"])
    if not is_manager_role:
        if user_id_to_assign and user_id_to_assign != creator.id:
            raise ApiKeyPermissionError("You can only create API keys for yourself.")
        if proxy_name:
            raise ApiKeyPermissionError("You cannot create proxy keys.")
        user_id_to_assign = creator.id # Default to self
    
    async with get_db_connection() as conn:
        # If creating for a CUE user, validate that the creator has access to them
        if user_id_to_assign:
            # Re-use the new helper logic for this check
            key_info_for_check = {'user_id': user_id_to_assign, 'proxy_user_name': None, 'ngroup_id': None}
            if not is_manager_role and user_id_to_assign != creator.id:
                 raise ApiKeyPermissionError("You can only create API keys for yourself.")
            elif is_manager_role and user_id_to_assign != creator.id:
                 can_access = await _can_manager_access_key(creator, key_info_for_check, conn)
                 if not can_access:
                     raise ApiKeyPermissionError("You do not have permission to create a key for this user.")

        # If creating a proxy key, validate the creator has access to the ngroup
        elif ngroup_id_for_proxy:
            if "admin" not in creator.roles and (not is_manager_role or str(ngroup_id_for_proxy) not in creator.ngroups):
                raise ApiKeyPermissionError("You do not have permission to create a key for this ngroup.")

    raw_key, prefix = _generate_secure_key()
    key_hash = _hash_key(raw_key)
    key_display_suffix = raw_key[-7:]
    
    if request.expires_at:
        expires_at = request.expires_at
    else:
        expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)

    async with get_db_connection() as conn:
        key_id = await api_key_db.store_api_key(
            conn, key_hash, prefix, request.name, request.scopes, user_id_to_assign,
            creator.id, proxy_name, ngroup_id_for_proxy, expires_at, key_display_suffix
        )

    logger.info("api_key.created", key_id=str(key_id), creator_id=str(creator.id))
    return {"id": key_id, "name": request.name, "key": raw_key}

async def list_api_keys(user: AuthUser) -> List[ApiKeyInfo]:
    """Retrieves API keys based on the user's role and active ngroup."""
    ngroup_filter = None
    is_manager_role = any(role in user.roles for role in ["admin", "daac_manager", "daac_staff"])
    if is_manager_role and user.active_ngroup_id:
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

        # ---Using the new permission helper ---
        can_manage = False
        is_manager_role = any(role in user.roles for role in ["admin", "daac_manager", "daac_staff"])

        if key_to_update['created_by_user_id'] == user.id:
            can_manage = True
        elif is_manager_role:
            can_manage = await _can_manager_access_key(user, key_to_update, conn)

        if not can_manage:
            raise ApiKeyPermissionError("You do not have permission to update this key.")

        await api_key_db.update_api_key(conn, key_id, update_request.model_dump())
    logger.info("api_key.updated", key_id=str(key_id), updater_id=str(user.id))

async def revoke_api_key(key_id: UUID, user: AuthUser):
    """Revokes an API key after checking permissions."""
    # We can reuse the permission logic from update_api_key
    await update_api_key(key_id, ApiKeyUpdateRequest(is_active=False), user) # This also serves to check permissions
    
    async with get_db_connection() as conn:
        success = await api_key_db.revoke_api_key(conn, key_id)
    if not success:
        # This case is unlikely if the update_api_key call succeeded, but good for safety
        raise ApiKeyNotFoundError("API Key not found.")
    logger.info("api_key.revoked", key_id=str(key_id), revoker_id=str(user.id))