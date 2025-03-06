from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from typing import List

from utils.cueuser_ngroup import (
    create_cueuser_ngroup_association,
    delete_cueuser_ngroup_association,
    list_ngroups_for_cueuser,
    list_cueusers_in_ngroup,
    CueuserNgroupAssociationError,
    CueuserNgroupNotFoundError
)
from lambda_utils.type_util.cueuser_ngroup import CueuserNgroupCreate



router = APIRouter(prefix="/cueuser-ngroup", tags=["cueuser-ngroup"])

@router.post("/associate", response_model=bool)
async def associate_cueuser_with_ngroup_endpoint(data: CueuserNgroupCreate, ):
    try:
        return await create_cueuser_ngroup_association(data)
    except CueuserNgroupAssociationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/dissociate", response_model=bool)
async def dissociate_cueuser_from_ngroup_endpoint(data: CueuserNgroupCreate, ):
    try:
        return await delete_cueuser_ngroup_association(data)
    except CueuserNgroupNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/cueuser/{cueuser_id}/ngroups", response_model=List[UUID])
async def list_ngroups_for_cueuser_endpoint(cueuser_id: UUID, ):
    try:
        return await list_ngroups_for_cueuser(cueuser_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ngroup/{ngroup_id}/cueusers", response_model=List[UUID])
async def list_cueusers_in_ngroup_endpoint(ngroup_id: UUID, ):
    try:
        return await list_cueusers_in_ngroup(ngroup_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))