# ==============================================================================
# File: src/python/api/v2/utils/provider.py (Corrected)
# --- MODIFIED to pass the request object on cross-utility calls ---
# ==============================================================================
from uuid import UUID
from typing import List, Optional, Dict, Any
from v2.type_util.auth import AuthUser
import structlog
from fastapi import Request

# No longer need get_db_connection
# from core.db import get_db_connection 
from v2.database_util import provider as provider_db
from v2.type_util.provider import ProviderCreate, ProviderUpdate
# We need to import the user utils to validate the point_of_contact
from v2.utils import cueuser as cueuser_utils

logger = structlog.get_logger(__name__)

class ProviderNotFoundError(Exception):
    """Custom exception raised when a provider is not found."""
    def __init__(self, provider_id: UUID):
        self.provider_id = provider_id
        super().__init__(f"Provider not found with ID: {provider_id}")

async def create_provider(request: Request, provider: ProviderCreate) -> Dict[str, Any]:
    """Creates a new provider record after validating dependencies."""
    # Validate that the point_of_contact user exists.
    try:
        # --- Pass the request object to the user utility function ---
        await cueuser_utils.get_user_profile(request, provider.point_of_contact)
    except cueuser_utils.UserNotFoundError as e:
        raise ValueError(f"Point of contact user with ID '{provider.point_of_contact}' not found.") from e

    async with request.state.pool.acquire() as conn:
        new_provider = await provider_db.create_provider(
            conn, provider.ngroup_id, provider.short_name, provider.long_name,
            provider.can_upload, provider.point_of_contact
        )
    logger.info("provider.created", provider_id=str(new_provider['id']))
    return dict(new_provider)

async def get_provider(request: Request, provider_id: UUID) -> Dict[str, Any]:
    """Retrieves a provider record by its ID."""
    async with request.state.pool.acquire() as conn:
        provider = await provider_db.get_provider_by_id(conn, provider_id)
    if not provider:
        raise ProviderNotFoundError(provider_id=provider_id)
    return dict(provider)

async def list_providers(
    request: Request,
    user: AuthUser, # Accept the full user object for role checks
    active_ngroup_id: Optional[str] # Accept the optional ngroup ID string
) -> List[Dict[str, Any]]:
    """Retrieves all provider records based on the user's roles and active ngroup."""

    # Convert string UUID from header to UUID object, or None
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None

    async with request.state.pool.acquire() as conn:
        # Call the new, more powerful list_providers function
        records = await provider_db.list_providers(
            conn,
            requesting_user=user.model_dump(),
            active_ngroup_id=ngroup_id_to_filter
        )
    return [dict(r) for r in records]

async def list_providers_for_form(request: Request, ngroup_id: UUID) -> List[Dict[str, Any]]:
    """Retrieves a simplified list of providers for a given ngroup."""
    async with request.state.pool.acquire() as conn:
        records = await provider_db.list_providers_for_form(conn, ngroup_id)
    return [dict(r) for r in records]

async def update_provider(request: Request, provider_id: UUID, provider_update: ProviderUpdate) -> Dict[str, Any]:
    """Updates an existing provider record."""
    update_data = provider_update.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    
    # If point_of_contact is being updated, validate the new user exists.
    if "point_of_contact" in update_data:
        try:
            # --- Pass the request object to the user utility function ---
            await cueuser_utils.get_user_profile(request, update_data["point_of_contact"])
        except cueuser_utils.UserNotFoundError as e:
            raise ValueError(f"New point of contact user with ID '{update_data['point_of_contact']}' not found.") from e

    async with request.state.pool.acquire() as conn:
        updated_provider = await provider_db.update_provider(conn, provider_id, update_data)
    
    if not updated_provider:
        raise ProviderNotFoundError(provider_id=provider_id)
    
    logger.info("provider.updated", provider_id=str(provider_id))
    return dict(updated_provider)

async def delete_provider(request: Request, provider_id: UUID):
    """Deletes a provider record by its ID."""
    async with request.state.pool.acquire() as conn:
        success = await provider_db.delete_provider(conn, provider_id)
    if not success:
        raise ProviderNotFoundError(provider_id=provider_id)
    logger.info("provider.deleted", provider_id=str(provider_id))

