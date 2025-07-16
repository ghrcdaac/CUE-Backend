from fastapi import APIRouter, HTTPException
from uuid import UUID
from typing import List

from v2.utils.cueuser_auth import create_cueuser_auth, get_cueuser_auth, update_cueuser_auth, delete_cueuser_auth, list_cueuser_auths, CueuserAuthNotFoundError
from lambda_utils.type_util.cueuser_auth import CueuserAuthCreate, CueuserAuthReturn, CueuserAuthUpdate

router = APIRouter(prefix="/cueuser-auth", tags=["cueuser-auth"])

@router.post("/", response_model=bool)
async def create_cueuser_auth_endpoint(cueuser_auth: CueuserAuthCreate):
    try:
        return await create_cueuser_auth(cueuser_auth)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{cueuser_auth_id}", response_model=CueuserAuthReturn)
async def get_cueuser_auth_endpoint(cueuser_auth_id: UUID):
    try:
        cueuser_auth = await get_cueuser_auth(cueuser_auth_id)
        return cueuser_auth
    except CueuserAuthNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{cueuser_auth_id}", response_model=CueuserAuthReturn)
async def update_cueuser_auth_endpoint(cueuser_auth_id: UUID, cueuser_auth_update: CueuserAuthUpdate):
    try:
        updated_cueuser_auth = await update_cueuser_auth(cueuser_auth_id, cueuser_auth_update)
        return updated_cueuser_auth
    except CueuserAuthNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{cueuser_auth_id}", response_model=bool)
async def delete_cueuser_auth_endpoint(cueuser_auth_id: UUID):
    try:
        success = await delete_cueuser_auth(cueuser_auth_id)
        return success
    except CueuserAuthNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[CueuserAuthReturn])
async def list_cueuser_auths_endpoint():
    try:
        return await list_cueuser_auths()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))