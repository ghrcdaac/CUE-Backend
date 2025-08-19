# ==============================================================================
# File: src/python/api/v2/endpoints/provider.py (Final)
# Purpose: Provides the v2 REST API endpoints for provider management.
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from typing import List

from core.security import require_privilege
from v2.utils import provider as provider_utils
from v2.type_util.provider import (
    ProviderCreate, ProviderUpdate, ProviderResponse, ProviderListResponse
)

router = APIRouter(prefix="/providers", tags=["V2 - Providers"])

@router.post("/", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_privilege("create_provider"))])
async def create_provider_endpoint(provider: ProviderCreate):
    """Creates a new provider. Requires 'create_provider' privilege."""
    try:
        new_provider = await provider_utils.create_provider(provider)
        return ProviderResponse.model_validate(new_provider)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.get("/for-application-form", response_model=List[ProviderListResponse])
async def list_providers_for_application_form(ngroup_id: UUID = Query(..., description="The ngroup ID to filter providers by.")):
    """
    A public endpoint to retrieve a simplified list of providers for a given ngroup.
    Used to populate the dropdown in the user application form.
    """
    try:
        return await provider_utils.list_providers_for_form(ngroup_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve providers for the application form.")

@router.get("/", response_model=List[ProviderResponse], dependencies=[Depends(require_privilege("view_provider"))])
async def list_providers_endpoint(ngroup_id: UUID = Query(..., description="The ngroup ID to filter providers by.")):
    """Retrieves all provider records for a specific ngroup. Requires 'view_provider' privilege."""
    try:
        return await provider_utils.list_providers(ngroup_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.get("/{provider_id}", response_model=ProviderResponse, dependencies=[Depends(require_privilege("view_provider"))])
async def get_provider_endpoint(provider_id: UUID):
    """Retrieves a single provider by its ID."""
    try:
        provider = await provider_utils.get_provider(provider_id)
        return ProviderResponse.model_validate(provider)
    except provider_utils.ProviderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.patch("/{provider_id}", response_model=ProviderResponse, dependencies=[Depends(require_privilege("manage_provider"))])
async def update_provider_endpoint(provider_id: UUID, provider_update: ProviderUpdate):
    """Updates an existing provider. Requires 'manage_provider' privilege."""
    try:
        updated_provider = await provider_utils.update_provider(provider_id, provider_update)
        return ProviderResponse.model_validate(updated_provider)
    except provider_utils.ProviderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_privilege("admin"))])
async def delete_provider_endpoint(provider_id: UUID):
    """Deletes a provider. Requires 'admin' privilege."""
    try:
        await provider_utils.delete_provider(provider_id)
    except provider_utils.ProviderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")
