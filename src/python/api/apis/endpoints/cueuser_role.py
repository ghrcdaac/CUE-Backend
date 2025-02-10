from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from typing import List

from utils.cueuser_role import (
    create_cueuser_role_association,
    delete_cueuser_role_association,
    list_roles_for_cueuser,
    list_cueusers_with_role,
    CueuserRoleAssociationError,
    CueuserRoleNotFoundError
)
from lambda_utils.type_util.cueuser_role import CueuserRoleCreate
from lambda_utils.type_util.cueuser import CueuserAuth
from utils.auth import get_current_user

router = APIRouter(prefix="/cueuser-role", tags=["cueuser-role"])

@router.post("/associate", response_model=bool)
async def associate_cueuser_with_role_endpoint(data: CueuserRoleCreate, user: CueuserAuth = Depends(get_current_user)):
    try:
        return await create_cueuser_role_association(data)
    except CueuserRoleAssociationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/dissociate", response_model=bool)
async def dissociate_cueuser_from_role_endpoint(data: CueuserRoleCreate, user: CueuserAuth = Depends(get_current_user)):
    try:
        return await delete_cueuser_role_association(data)
    except CueuserRoleNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/cueuser/{cueuser_id}/roles", response_model=List[UUID])
async def list_roles_for_cueuser_endpoint(cueuser_id: UUID, user: CueuserAuth = Depends(get_current_user)):
    try:
        return await list_roles_for_cueuser(cueuser_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/role/{role_id}/cueusers", response_model=List[UUID])
async def list_cueusers_with_role_endpoint(role_id: UUID, user: CueuserAuth = Depends(get_current_user)):
    try:
        return await list_cueusers_with_role(role_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))