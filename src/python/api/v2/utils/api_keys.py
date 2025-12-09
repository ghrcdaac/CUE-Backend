# ==============================================================================
# File: src/python/api/v2/utils/api_keys.py
# ==============================================================================
import secrets
import hashlib
from uuid import UUID
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import structlog
from fastapi import Request

from v2.database_util import api_keys as api_key_db
from v2.database_util import cueuser as user_db
from v2.type_util.api_keys import ApiKeyCreateRequest, ApiKeyUpdateRequest, ApiKeyInfo
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

async def _can_manager_access_key(manager: AuthUser, key_info: Dict[str, Any], conn) -> bool:
    """Checks if a manager has permission to access a given key."""
    # This helper is useful for checking manager-specific group access.
    if "admin" in manager.roles:
        return True
    
    key_ngroup_id = key_info.get('ngroup_id')
    if key_ngroup_id and str(key_ngroup_id) in manager.ngroups:
        return True

    key_user_id = key_info.get('user_id')
    if key_user_id:
        target_user = await user_db.get_user_by_id(conn, key_user_id)
        if not target_user:
            return False
        
        target_ngroups_raw = target_user.get('ngroups', [])
        target_user_ngroups = {str(ng['id']) if isinstance(ng, dict) else str(ng) for ng in target_ngroups_raw if ng}
        
        if set(manager.ngroups).intersection(target_user_ngroups):
            return True
            
    return False


async def create_api_key(request: Request, create_body: ApiKeyCreateRequest, creator: AuthUser) -> Dict[str, Any]:
    """Orchestrates the creation of a new API key based on its type."""
    creator_roles = set(creator.roles)
    key_type = create_body.key_type
    
    is_privileged_creator = creator_roles.intersection({'admin', 'security', 'daac_manager', 'daac_staff'})
    if key_type in ['managed_user', 'proxy'] and not is_privileged_creator:
        raise ApiKeyPermissionError("You do not have permission to create managed or proxy keys.")

    user_id_to_assign = None
    ngroup_id_to_assign = create_body.ngroup_id

    if key_type == 'personal':
        user_id_to_assign = creator.id
    elif key_type == 'managed_user':
        user_id_to_assign = create_body.target_user_id
    
    raw_key, prefix = _generate_secure_key()
    key_hash = _hash_key(raw_key)
    key_display_suffix = raw_key[-4:]
    expires_at = create_body.expires_at or (datetime.now(timezone.utc) + timedelta(days=create_body.expires_in_days))

    # All database operations are now inside a single `async with` block.
    # The 'conn' object is acquired once and used for all subsequent calls
    # before being automatically released at the end of the block.
    async with request.state.pool.acquire() as conn:
        # 1. Perform permission checks that require database access
        if key_type == 'managed_user':
            key_info_for_check = {'user_id': user_id_to_assign, 'ngroup_id': ngroup_id_to_assign}
            if not await _can_manager_access_key(creator, key_info_for_check, conn):
                raise ApiKeyPermissionError("You do not have permission to create a key for this user or group.")
        
        if key_type == 'proxy':
             if 'admin' not in creator_roles and str(ngroup_id_to_assign) not in creator.ngroups:
                 raise ApiKeyPermissionError("You do not have permission to create a key for this group.")

        # 2. Store the key in the database using the same connection
        key_id = await api_key_db.store_api_key(
            conn, key_hash, prefix, create_body.name, create_body.scopes, key_type,
            user_id_to_assign, creator.id, create_body.proxy_user_name,
            ngroup_id_to_assign, expires_at, key_display_suffix
        )

    logger.info("api_key.created", key_id=str(key_id), creator_id=str(creator.id), key_type=key_type)
    return {"id": key_id, "name": create_body.name, "key": raw_key}

# Simplified to pass the full user object to the database layer.
async def list_api_keys(request: Request, user: AuthUser, page: int, page_size: int, active_ngroup_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves API keys based on the user's role and active ngroup from the header."""
    offset = (page - 1) * page_size
    async with request.state.pool.acquire() as conn:
        # Convert the string ID from the header to a UUID object for the database function
        active_ngroup_uuid = UUID(active_ngroup_id) if active_ngroup_id else None

        total = await api_key_db.count_api_keys(
            conn=conn, 
            requesting_user=user.model_dump(), 
            active_ngroup_id=active_ngroup_uuid,
            )
        result = []
        if total > 0:
            keys_data = await api_key_db.list_api_keys(
                conn,
                requesting_user=user.model_dump(),
                active_ngroup_id=active_ngroup_uuid,
                page_size = page_size,
                offset = offset
            )
            result = [dict(r) for r in keys_data]
            
    return {
        "api_keys": result,
        "page": page,
        "page_size": page_size,
        "total": total,
    }

# Permission check now includes an override for admin/security roles.
async def update_api_key(request: Request, key_id: UUID, update_request: ApiKeyUpdateRequest, user: AuthUser):
    """Updates an API key's status after checking permissions."""
    async with request.state.pool.acquire() as conn:
        key_to_update = await api_key_db.get_api_key_by_id(conn, key_id)
        if not key_to_update:
            raise ApiKeyNotFoundError("API Key not found.")

        user_roles = set(user.roles)
        can_manage = False

        # 1. Admin/Security roles have universal access.
        if user_roles.intersection({'admin', 'security'}):
            can_manage = True
        # 2. Check if the user owns the key (for personal keys).
        elif key_to_update['key_type'] == 'personal' and key_to_update['user_id'] == user.id:
            can_manage = True
        # 3. Check if the user is a manager of the key's group.
        elif user_roles.intersection({'daac_manager', 'daac_staff'}):
            can_manage = await _can_manager_access_key(user, key_to_update, conn)

        if not can_manage:
            raise ApiKeyPermissionError("You do not have permission to update this key.")

        await api_key_db.update_api_key(conn, key_id, update_request.model_dump())
    logger.info("api_key.updated", key_id=str(key_id), updater_id=str(user.id))

# Permission check now includes an override for admin/security roles.
async def revoke_api_key(request: Request, key_id: UUID, user: AuthUser):
    """Soft-deletes an API key after checking permissions."""
    async with request.state.pool.acquire() as conn:
        key_to_revoke = await api_key_db.get_api_key_by_id(conn, key_id)
        if not key_to_revoke:
            raise ApiKeyNotFoundError("API Key not found.")

        user_roles = set(user.roles)
        can_manage = False

        # 1. Admin/Security roles have universal access.
        if user_roles.intersection({'admin', 'security'}):
            can_manage = True
        # 2. Check if the user owns the key (for personal keys).
        elif key_to_revoke['key_type'] == 'personal' and key_to_revoke['user_id'] == user.id:
            can_manage = True
        # 3. Check if the user is a manager of the key's group.
        elif user_roles.intersection({'daac_manager', 'daac_staff'}):
            can_manage = await _can_manager_access_key(user, key_to_revoke, conn)
        
        if not can_manage:
            raise ApiKeyPermissionError("You do not have permission to revoke this key.")
        
        success = await api_key_db.soft_delete_api_key(conn, key_id)
        if not success:
            raise ApiKeyNotFoundError("API Key could not be revoked.")

    logger.info("api_key.revoked (soft_delete)", key_id=str(key_id), revoker_id=str(user.id))

# Accepts 'request' and uses the connection pool
async def record_api_key_usage(request: Request, key_id: UUID):
    """Records the usage of an API key by updating its last_used_at timestamp."""
    async with request.state.pool.acquire() as conn:
        success = await api_key_db.record_key_usage(conn, key_id)
        if not success:
            logger.warning("api_key.record_usage.not_found", key_id=str(key_id))