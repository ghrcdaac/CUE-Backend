from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from typing import List

from utils.role_privilege import (
    create_role_privilege_association,
    delete_role_privilege_association,
    list_privileges_for_role,
    list_roles_with_privilege,
    RolePrivilegeAssociationError,
    RolePrivilegeNotFoundError
)
from lambda_utils.type_util.role_privilege import RolePrivilegeCreate
from lambda_utils.type_util.cueuser import CueuserAuth
from utils.auth import get_current_user

router = APIRouter(prefix="/role-privilege", tags=["role-privilege"])

@router.post("/associate", response_model=bool)
async def associate_role_with_privilege_endpoint(data: RolePrivilegeCreate, user: CueuserAuth = Depends(get_current_user)):
    try:
        return await create_role_privilege_association(data)
    except RolePrivilegeAssociationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/dissociate", response_model=bool)
async def dissociate_role_from_privilege_endpoint(data: RolePrivilegeCreate, user: CueuserAuth = Depends(get_current_user)):
    try:
        return await delete_role_privilege_association(data)
    except RolePrivilegeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/role/{role_id}/privileges", response_model=List[str])
async def list_privileges_for_role_endpoint(role_id: UUID, user: CueuserAuth = Depends(get_current_user)):
    try:
        return await list_privileges_for_role(role_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/privilege/{privilege}/roles", response_model=List[UUID])
async def list_roles_with_privilege_endpoint(privilege: str, user: CueuserAuth = Depends(get_current_user)):
    try:
        return await list_roles_with_privilege(privilege)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))