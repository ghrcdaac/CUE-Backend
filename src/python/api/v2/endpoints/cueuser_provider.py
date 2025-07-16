from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from typing import List

from v2.utils.cueuser_provider import (
    create_cueuser_provider_association,
    delete_cueuser_provider_association,
    list_providers_for_cueuser,
    list_cueusers_for_provider,
    CueuserProviderAssociationError,
    CueuserProviderNotFoundError
)
from lambda_utils.type_util.cueuser_provider import CueuserProviderCreate



router = APIRouter(prefix="/cueuser-provider", tags=["cueuser-provider"])

@router.post("/associate", response_model=bool)
async def associate_cueuser_with_provider_endpoint(data: CueuserProviderCreate, ):
    try:
        return await create_cueuser_provider_association(data)
    except CueuserProviderAssociationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/dissociate", response_model=bool)
async def dissociate_cueuser_from_provider_endpoint(data: CueuserProviderCreate, ):
    try:
        return await delete_cueuser_provider_association(data)
    except CueuserProviderNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/cueuser/{cueuser_id}/providers", response_model=List[UUID])
async def list_providers_for_cueuser_endpoint(cueuser_id: UUID, ):
    try:
        return await list_providers_for_cueuser(cueuser_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/provider/{provider_id}/cueusers", response_model=List[UUID])
async def list_cueusers_for_provider_endpoint(provider_id: UUID, ):
    try:
        return await list_cueusers_for_provider(provider_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))