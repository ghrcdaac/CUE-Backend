from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from typing import List, Optional

from utils.provider import create_provider, get_provider, update_provider, delete_provider, list_providers, ProviderNotFoundError, get_provider_by_lookup
from lambda_utils.type_util.provider import ProviderCreate, ProviderReturn, ProviderUpdate

router = APIRouter(prefix="/provider", tags=["provider"])

@router.post("/", response_model=ProviderReturn)
async def create_provider_endpoint(provider: ProviderCreate):
    try:
        return await create_provider(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/find", response_model=ProviderReturn)
async def lookup_provider_endpoint(
    short_name: Optional[str] = Query(None, description="Provider Short Name to search for"),
    long_name: Optional[str] = Query(None, description="Provider Long Name to search for")
):
    try:
        provider = await get_provider_by_lookup(short_name, long_name)
        return provider
    except ProviderNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@router.get("/{provider_id}", response_model=ProviderReturn)
async def get_provider_endpoint(provider_id: UUID):
    try:
        provider = await get_provider(provider_id)
        return provider
    except ProviderNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{provider_id}", response_model=ProviderReturn)
async def update_provider_endpoint(provider_id: UUID, provider_update: ProviderUpdate):
    try:
        updated_provider = await update_provider(provider_id, provider_update)
        return updated_provider
    except ProviderNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{provider_id}", response_model=bool)
async def delete_provider_endpoint(provider_id: UUID):
    try:
        success = await delete_provider(provider_id)
        return success
    except ProviderNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[ProviderReturn])
async def list_providers_endpoint(
        ngroup_id: Optional[UUID] = Query(None, description="Filter by ngroup ID"),
        can_upload: Optional[bool] = Query(None, description="Filter by can_upload status")
):
    try:
        return await list_providers(ngroup_id, can_upload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
