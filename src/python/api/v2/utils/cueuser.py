# ==============================================================================
# File: src/python/api/v2/utils/cueuser.py (Updated)
# --- MODIFIED to use the shared connection pool from the request state ---
# ==============================================================================
from uuid import UUID
from typing import Dict, Any, List, Optional
import structlog
import json
from fastapi import Request # <-- Import Request

from v2.type_util.auth import AuthUser
# --- REMOVED: from core.db import get_db_connection ---
from v2.database_util import cueuser as user_db
from v2.database_util import role as role_db
from v2.type_util.cueuser import UserUpdateRequest

logger = structlog.get_logger(__name__)

class UserNotFoundError(Exception):
    pass

def _parse_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to parse JSON string fields from the DB into Python lists."""
    if not user_data:
        return None
    
    parsed_data = dict(user_data)
    
    for key in ["roles", "ngroups", "privileges"]:
        if isinstance(parsed_data.get(key), str):
            try:
                parsed_data[key] = json.loads(parsed_data[key])
            except json.JSONDecodeError:
                logger.warning("db.json.parse_error", field=key, value=parsed_data[key])
                parsed_data[key] = []
    return parsed_data

# --- MODIFIED: Functions now accept the `request` object ---

async def create_new_user(
    request: Request,
    user_id: UUID, email: str, name: str, cueusername: str, role_id: UUID,
    edpub_id: Optional[str] = None,
    ngroup_ids: Optional[List[UUID]] = None,
    provider_ids: Optional[List[UUID]] = None
) -> Dict[str, Any]:
    """Orchestrates creating a user in the local database."""
    if not ngroup_ids and not provider_ids:
        raise ValueError("User must be associated with at least one ngroup or provider.")

    async with request.state.pool.acquire() as conn:
        async with conn.transaction():
            exists = await user_db.user_exists_by_id(conn, user_id)
            if exists:
                raise ValueError(f"User with ID {user_id} already exists in the CUE database.")

            await user_db.create_user(conn, user_id, email, name, cueusername, edpub_id)
            await user_db.assign_role_to_user(conn, user_id, role_id)
            if ngroup_ids:
                await user_db.assign_ngroups_to_user(conn, user_id, ngroup_ids)
            if provider_ids:
                await user_db.assign_providers_to_user(conn, user_id, provider_ids)
    
    logger.info("user.created_locally", user_id=str(user_id))
    return await get_user_profile(request, user_id)

async def get_user_profile(request: Request, user_id: UUID) -> Dict[str, Any]:
    """
    Fetches and parses a user's complete profile. If the user is an admin,
    it ensures all system privileges are included.
    """
    async with request.state.pool.acquire() as conn:
        user_data = await user_db.get_user_by_id(conn, user_id)
        if not user_data:
            raise UserNotFoundError()
        
        user_profile = _parse_user_data(user_data)

        if "admin" in user_profile.get("roles", []):
            logger.info("user.is_admin.fetching_all_privileges", user_id=str(user_id))
            all_privileges = await role_db.list_all_privileges(conn)
            user_profile["privileges"] = all_privileges
    
    return user_profile

async def list_users(request: Request) -> List[Dict[str, Any]]:
    """Retrieves a list of all users."""
    async with request.state.pool.acquire() as conn:
        users_data = await user_db.list_users(conn)
    return [_parse_user_data(user) for user in users_data]

async def get_user_profile_by_username(request: Request, cueusername: str) -> Dict[str, Any]:
    """Fetches and parses a user's complete profile by their username."""
    async with request.state.pool.acquire() as conn:
        user_data = await user_db.get_user_by_username(conn, cueusername)
    if not user_data:
        raise UserNotFoundError()
    return _parse_user_data(user_data)

async def find_users_by_criteria(request: Request, email: Optional[str], cueusername: Optional[str], name: Optional[str], edpub_id: Optional[str]) -> List[Dict[str, Any]]:
    """Finds users matching various criteria and parses the results."""
    if not any([email, cueusername, name, edpub_id]):
        raise ValueError("At least one search criterion must be provided.")
    async with request.state.pool.acquire() as conn:
        users_data = await user_db.find_user(conn, email, cueusername, name, edpub_id)
    return [_parse_user_data(user) for user in users_data]

async def get_users_by_role(request: Request, role_id: UUID) -> List[Dict[str, Any]]:
    """Lists all users assigned to a specific role."""
    async with request.state.pool.acquire() as conn:
        users_data = await user_db.list_users_by_role(conn, role_id)
    return [dict(user) for user in users_data]

async def delete_user_fully(request: Request, user_id: UUID):
    """Deletes a user and all their associations from the local CUE database."""
    async with request.state.pool.acquire() as conn:
        async with conn.transaction():
            await user_db.remove_all_user_associations(conn, user_id)
            deleted_in_db = await user_db.delete_user(conn, user_id)
            if not deleted_in_db:
                raise UserNotFoundError(f"User with ID {user_id} not found.")
    
    logger.info("user.deleted_locally", user_id=str(user_id))

async def update_user_details(request: Request, user_id: UUID, update_request: UserUpdateRequest) -> Dict[str, Any]:
    """Updates a user's core details."""
    update_data = update_request.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    
    async with request.state.pool.acquire() as conn:
        await user_db.update_user(conn, user_id, update_data)
    
    return await get_user_profile(request, user_id)

async def update_user_role(request: Request, user_id: UUID, role_id: UUID, current_user: AuthUser) -> Dict[str, Any]:
    """
    Updates a user's role after performing permission checks.
    For simplicity in this system, it replaces all existing roles with the new one.
    """
    is_admin = "admin" in current_user.roles
    is_manager = "daac_manager" in current_user.roles
    
    if not is_admin:
        async with request.state.pool.acquire() as conn:
            target_role = await role_db.get_role_by_id(conn, role_id)
            if not target_role:
                raise ValueError("Target role not found.")

            allowed_roles = set()
            if is_manager:
                allowed_roles.update(["daac_staff", "daac_observer", "provider"])
            
            if "security" in current_user.roles:
                allowed_roles.add("security")
            
            if target_role['short_name'] not in allowed_roles:
                raise ValueError("You do not have permission to assign this role.")

    async with request.state.pool.acquire() as conn:
        await user_db.update_user_roles(conn, user_id, [role_id])
    
    logger.info("user.role.updated", user_id=str(user_id), new_role_id=str(role_id), updater_id=str(current_user.id))
    return await get_user_profile(request, user_id)
