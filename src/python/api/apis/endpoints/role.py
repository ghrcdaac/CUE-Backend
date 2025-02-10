from fastapi import APIRouter, HTTPException, Query, Depends
from uuid import UUID
from typing import List, Optional

from utils.role import create_role, get_role, update_role, delete_role, list_roles, get_role_by_lookup, RoleNotFoundError
from lambda_utils.type_util.role import RoleCreate, RoleReturn, RoleUpdate
from lambda_utils.type_util.cueuser import CueuserAuth
from utils.auth import get_current_user

router = APIRouter(prefix="/role", tags=["role"])

@router.post("/", response_model=RoleReturn)
async def create_role_endpoint(role: RoleCreate, user: CueuserAuth = Depends(get_current_user)):
    try:
        return await create_role(role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/find", response_model=RoleReturn)
async def lookup_role_endpoint(
    short_name: Optional[str] = Query(None, description="Role Short Name to search for"),
    long_name: Optional[str] = Query(None, description="Role Long Name to search for"),
    user: CueuserAuth = Depends(get_current_user)
):
    try:
        role = await get_role_by_lookup(short_name, long_name)
        return role
    except RoleNotFoundError as e:  # Catch the exception as 'e'
        raise HTTPException(status_code=404, detail=str(e))  
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{role_id}", response_model=RoleReturn)
async def get_role_endpoint(role_id: UUID, user: CueuserAuth = Depends(get_current_user)):
    try:
        role = await get_role(role_id)
        return role
    except RoleNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{role_id}", response_model=RoleReturn)
async def update_role_endpoint(role_id: UUID, role_update: RoleUpdate, user: CueuserAuth = Depends(get_current_user)):
    try:
        updated_role = await update_role(role_id, role_update)
        return updated_role
    except RoleNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{role_id}", response_model=bool)
async def delete_role_endpoint(role_id: UUID, user: CueuserAuth = Depends(get_current_user)):
    try:
        success = await delete_role(role_id)
        return success
    except RoleNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[RoleReturn])
async def list_roles_endpoint(user: CueuserAuth = Depends(get_current_user)):
    try:
        return await list_roles()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
