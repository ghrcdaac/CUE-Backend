# ==============================================================================
# File: src/python/api/v2/endpoints/provider.py
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Header
from uuid import UUID
from typing import List, Optional

from core.security import require_privilege, get_current_user
from v2.type_util.auth import AuthUser
from v2.utils import provider as provider_utils
from v2.type_util.provider import (
    ProviderCreate, ProviderUpdate, ProviderResponse, ProviderListResponse, PaginatedProviderResponse
)

router = APIRouter(prefix="/providers", tags=["V2 - Providers"])

@router.post("/", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_privilege("provider:create"))])
async def create_provider_endpoint(request: Request, provider: ProviderCreate):
    """Creates a new provider. Requires 'provider:create' privilege."""
    try:
        new_provider = await provider_utils.create_provider(request, provider)
        return ProviderResponse.model_validate(new_provider)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/for-application-form", response_model=List[ProviderListResponse])
async def list_providers_for_application_form(
    request: Request,
    ngroup_id: UUID = Query(..., description="The ngroup ID to filter providers by.")
):
    """
    A public endpoint to retrieve a simplified list of providers for a given ngroup.
    Used to populate the dropdown in the user application form.
    """
    try:
        return await provider_utils.list_providers_for_form(request, ngroup_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve providers for the application form.")

@router.get("/", response_model=PaginatedProviderResponse, dependencies=[Depends(require_privilege("provider:read"))])
async def list_providers_endpoint(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    # Read the active ngroup ID directly from the header
    active_ngroup_id: Optional[str] = Header(None, alias="x-active-ngroup-id"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Retrieves all provider records, filtered by the user's selected ngroup from the header.
    """
    try:
        # Pass the header value and the user object to the utility function
        return await provider_utils.list_providers(request, user, active_ngroup_id, page, page_size)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{provider_id}", response_model=ProviderResponse, dependencies=[Depends(require_privilege("provider:read"))])
async def get_provider_endpoint(request: Request, provider_id: UUID):
    """Retrieves a single provider by its ID. Requires 'provider:read' privilege."""
    try:
        provider = await provider_utils.get_provider(request, provider_id)
        return ProviderResponse.model_validate(provider)
    except provider_utils.ProviderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/{provider_id}", response_model=ProviderResponse, dependencies=[Depends(require_privilege("provider:update"))])
async def update_provider_endpoint(request: Request, provider_id: UUID, provider_update: ProviderUpdate):
    """Updates an existing provider. Requires 'provider:update' privilege."""
    try:
        updated_provider = await provider_utils.update_provider(request, provider_id, provider_update)
        return ProviderResponse.model_validate(updated_provider)
    except provider_utils.ProviderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_privilege("provider:delete"))])
async def delete_provider_endpoint(request: Request, provider_id: UUID):
    """Deletes a provider. Requires 'provider:delete' privilege."""
    try:
        await provider_utils.delete_provider(request, provider_id)
    except provider_utils.ProviderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

