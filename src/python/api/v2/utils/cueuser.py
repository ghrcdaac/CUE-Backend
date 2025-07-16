# ==============================================================================
# File: src/python/api/v2/utils/cueuser.py (Refactored)
# Purpose: Contains the business logic for user management, orchestrating
# calls to the database and Keycloak admin utilities.
# ==============================================================================
from uuid import UUID
from typing import Dict, Any, List, Optional
import structlog

from core.db import get_db_connection
from ..database_util import cueuser as user_db
from .keycloak_admin import KeycloakAdminClient, get_keycloak_admin_client
from ..type_util.cueuser import UserUpdateRequest

logger = structlog.get_logger(__name__)

class UserNotFoundError(Exception):
    pass

async def create_new_user(
    email: str, name: str, username: str, role_id: UUID, ngroup_ids: List[UUID], edpub_id: Optional[str],
    keycloak_client: KeycloakAdminClient
) -> Dict[str, Any]:
    """
    Orchestrates creating a user in Keycloak and the local database.
    This is a transactional operation.
    """
    keycloak_user_id_str: Optional[str] = None
    try:
        # 1. Create user in Keycloak first.
        keycloak_user_id_str = await keycloak_client.create_user(email, username, name, name.split(" ")[-1])
        keycloak_user_id = UUID(keycloak_user_id_str)

        # 2. Create user and associations in local DB within a transaction.
        async with get_db_connection() as conn:
            async with conn.transaction():
                await user_db.create_user(conn, keycloak_user_id, email, name, username, edpub_id)
                await user_db.assign_role_to_user(conn, keycloak_user_id, role_id)
                await user_db.assign_ngroups_to_user(conn, keycloak_user_id, ngroup_ids)
        
        # 3. Fetch and return the complete profile of the new user.
        return await get_user_profile(keycloak_user_id)

    except Exception as e:
        # If DB operation fails after Keycloak user was created, roll back Keycloak user.
        if keycloak_user_id_str:
            logger.error("db_create.failed.rolling_back_keycloak", error=str(e), keycloak_id=keycloak_user_id_str)
            await keycloak_client.delete_user(UUID(keycloak_user_id_str))
        raise e # Re-raise the original exception

async def get_user_profile(user_id: UUID) -> Dict[str, Any]:
    """Fetches a user's complete profile."""
    async with get_db_connection() as conn:
        user_data = await user_db.get_user_by_id(conn, user_id)
        if not user_data:
            raise UserNotFoundError()
        return dict(user_data)

async def get_user_profile_by_username(username: str) -> Dict[str, Any]:
    """Fetches a user's complete profile by their username."""
    async with get_db_connection() as conn:
        user_data = await user_db.get_user_by_username(conn, username)
        if not user_data:
            raise UserNotFoundError()
        return dict(user_data)

async def find_users_by_criteria(email: Optional[str], username: Optional[str], name: Optional[str], edpub_id: Optional[str]) -> List[Dict[str, Any]]:
    """Finds users matching various criteria."""
    if not any([email, username, name, edpub_id]):
        raise ValueError("At least one search criterion must be provided.")
    async with get_db_connection() as conn:
        return await user_db.find_user(conn, email, username, name, edpub_id)

async def get_users_by_role(role_id: UUID) -> List[Dict[str, Any]]:
    """Lists all users assigned to a specific role."""
    async with get_db_connection() as conn:
        return await user_db.list_users_by_role(conn, role_id)

async def delete_user_fully(user_id: UUID, keycloak_client: KeycloakAdminClient):
    """Deletes a user from the local DB (with associations) and Keycloak."""
    async with get_db_connection() as conn:
        # Explicitly delete associations first for a clean, auditable process
        await user_db.remove_all_user_associations(conn, user_id)
        deleted_in_db = await user_db.delete_user(conn, user_id)
        if not deleted_in_db:
            raise UserNotFoundError()
    
    # After successful DB deletion, delete from Keycloak.
    await keycloak_client.delete_user(user_id)

async def update_user_details(user_id: UUID, update_request: UserUpdateRequest) -> Dict[str, Any]:
    """Updates a user's core details."""
    update_data = update_request.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    
    async with get_db_connection() as conn:
        await user_db.update_user(conn, user_id, update_data)
    
    return await get_user_profile(user_id)
