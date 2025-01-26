from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from utils.privilege import create_privilege, get_privilege, update_privilege, delete_privilege, list_privileges, get_privilege_by_lookup, PrivilegeNotFoundError
from lambda_utils.type_util.privilege import PrivilegeCreate, PrivilegeReturn, PrivilegeUpdate

router = APIRouter(prefix="/privilege", tags=["privilege"])

@router.post("/", response_model=PrivilegeReturn)
async def create_privilege_endpoint(privilege: PrivilegeCreate):
    try:
        return await create_privilege(privilege)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/find", response_model=PrivilegeReturn)
async def lookup_privilege_endpoint(
    privilege: Optional[str] = Query(None, description="Privilege to search for")
):
    try:
        privilege = await get_privilege_by_lookup(privilege)
        return privilege
    except PrivilegeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{privilege_name}", response_model=PrivilegeReturn)
async def get_privilege_endpoint(privilege_name: str):
    try:
        privilege = await get_privilege(privilege_name)
        return privilege
    except PrivilegeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{privilege_name}", response_model=PrivilegeReturn)
async def update_privilege_endpoint(privilege_name: str, privilege_update: PrivilegeUpdate):
    try:
        updated_privilege = await update_privilege(privilege_name, privilege_update)
        return updated_privilege
    except PrivilegeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{privilege_name}", response_model=bool)
async def delete_privilege_endpoint(privilege_name: str):
    try:
        success = await delete_privilege(privilege_name)
        return success
    except PrivilegeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[PrivilegeReturn])
async def list_privileges_endpoint():
    try:
        return await list_privileges()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))