# ==============================================================================
# File: src/python/api/v2/utils/cueuser.py (Final)
# Purpose: Contains the business logic for user management.
# ==============================================================================
from uuid import UUID
from typing import Dict, Any, List, Optional
import structlog
import json

from core.db import get_db_connection
from v2.database_util import cueuser as user_db
from v2.database_util import role as role_db 
from v2.utils.auth import KeycloakClient
from v2.type_util.cueuser import UserUpdateRequest

logger = structlog.get_logger(__name__)

class UserNotFoundError(Exception):
    pass

def _parse_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper function to parse JSON string fields from the DB into Python lists.
    The asyncpg driver can return json/jsonb columns as strings.
    """
    if not user_data:
        return None
    
    parsed_data = dict(user_data)
    
    # --- Restore JSON parsing for fields returned as strings from the DB ---
    for key in ["roles", "ngroups", "privileges"]:
        if isinstance(parsed_data.get(key), str):
            try:
                parsed_data[key] = json.loads(parsed_data[key])
            except json.JSONDecodeError:
                logger.warning("db.json.parse_error", field=key, value=parsed_data[key])
                # Default to an empty list if parsing fails
                parsed_data[key] = []
        
    return parsed_data

async def create_new_user(
    email: str, name: str, cueusername: str, role_id: UUID,
    keycloak_client: KeycloakClient,
    edpub_id: Optional[str] = None,
    ngroup_ids: Optional[List[UUID]] = None,
    provider_ids: Optional[List[UUID]] = None
) -> Dict[str, Any]:
    """Orchestrates creating a user in Keycloak and the local database."""
    if not ngroup_ids and not provider_ids:
        raise ValueError("User must be associated with at least one ngroup or provider.")

    keycloak_user_id_str: Optional[str] = None
    try:
        name_parts = name.strip().split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        keycloak_user_id_str = await keycloak_client.create_user(email, cueusername, first_name, last_name)
        keycloak_user_id = UUID(keycloak_user_id_str)

        async with get_db_connection() as conn:
            async with conn.transaction():
                await user_db.create_user(conn, keycloak_user_id, email, name, cueusername, edpub_id)
                await user_db.assign_role_to_user(conn, keycloak_user_id, role_id)
                if ngroup_ids:
                    await user_db.assign_ngroups_to_user(conn, keycloak_user_id, ngroup_ids)
                if provider_ids:
                    await user_db.assign_providers_to_user(conn, keycloak_user_id, provider_ids)
        
        return await get_user_profile(keycloak_user_id)

    except Exception as e:
        if keycloak_user_id_str:
            logger.error("db_create.failed.rolling_back_keycloak", error=str(e), keycloak_id=keycloak_user_id_str)
            await keycloak_client.delete_user(UUID(keycloak_user_id_str))
        raise e

async def get_user_profile(user_id: UUID) -> Dict[str, Any]:
    """
    Fetches and parses a user's complete profile. If the user is an admin,
    it ensures all system privileges are included.
    """
    async with get_db_connection() as conn:
        user_data = await user_db.get_user_by_id(conn, user_id)
        if not user_data:
            raise UserNotFoundError()
        
        user_profile = _parse_user_data(user_data)

        if "admin" in user_profile.get("roles", []):
            logger.info("user.is_admin.fetching_all_privileges", user_id=str(user_id))
            all_privileges = await role_db.list_all_privileges(conn)
            user_profile["privileges"] = all_privileges
    
    return user_profile

async def list_users() -> List[Dict[str, Any]]:
    """Retrieves a list of all users."""
    async with get_db_connection() as conn:
        users_data = await user_db.list_users(conn)
        print(users_data)
    return [_parse_user_data(user) for user in users_data]

async def get_user_profile_by_username(cueusername: str) -> Dict[str, Any]:
    """Fetches and parses a user's complete profile by their username."""
    async with get_db_connection() as conn:
        user_data = await user_db.get_user_by_username(conn, cueusername)
    if not user_data:
        raise UserNotFoundError()
    return _parse_user_data(user_data)

async def find_users_by_criteria(email: Optional[str], cueusername: Optional[str], name: Optional[str], edpub_id: Optional[str]) -> List[Dict[str, Any]]:
    """Finds users matching various criteria and parses the results."""
    if not any([email, cueusername, name, edpub_id]):
        raise ValueError("At least one search criterion must be provided.")
    async with get_db_connection() as conn:
        users_data = await user_db.find_user(conn, email, cueusername, name, edpub_id)
    return [_parse_user_data(user) for user in users_data]

async def get_users_by_role(role_id: UUID) -> List[Dict[str, Any]]:
    """Lists all users assigned to a specific role."""
    async with get_db_connection() as conn:
        users_data = await user_db.list_users_by_role(conn, role_id)
    return [dict(user) for user in users_data]

async def delete_user_fully(user_id: UUID, keycloak_client: KeycloakClient):
    """Deletes a user from the local DB (with associations) and Keycloak."""
    async with get_db_connection() as conn:
        await user_db.remove_all_user_associations(conn, user_id)
        deleted_in_db = await user_db.delete_user(conn, user_id)
        if not deleted_in_db:
            raise UserNotFoundError()
    
    await keycloak_client.delete_user(user_id)

async def update_user_details(user_id: UUID, update_request: UserUpdateRequest) -> Dict[str, Any]:
    """Updates a user's core details."""
    update_data = update_request.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    
    async with get_db_connection() as conn:
        await user_db.update_user(conn, user_id, update_data)
    
    return await get_user_profile(user_id)
