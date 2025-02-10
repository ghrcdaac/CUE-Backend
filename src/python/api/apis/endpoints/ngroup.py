from fastapi import APIRouter, HTTPException, Query, Depends
from uuid import UUID
from typing import List, Optional

from utils.ngroup import create_ngroup, get_ngroup_id_by_name, get_ngroup, update_ngroup, delete_ngroup, list_ngroups, NgroupNotFoundError  
from lambda_utils.type_util.ngroup import NgroupCreate, NgroupReturn, NgroupUpdate
from lambda_utils.type_util.cueuser import CueuserAuth
from utils.auth import get_current_user

router = APIRouter(prefix="/ngroup", tags=["ngroup"])

@router.post("/", response_model=NgroupReturn)
async def create_ngroup_endpoint(ngroup: NgroupCreate, user: CueuserAuth = Depends(get_current_user)):
    return await create_ngroup(ngroup)

@router.get("/id", response_model=UUID)
async def get_ngroup_id_endpoint(
    short_name: Optional[str] = Query(None, alias="short_name"),
    long_name: Optional[str] = Query(None, alias="long_name"),
    user: CueuserAuth = Depends(get_current_user)
):
    try:
        ngroup_id = await get_ngroup_id_by_name(short_name, long_name)
        return ngroup_id
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NgroupNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{ngroup_id}", response_model=NgroupReturn)
async def get_ngroup_endpoint(ngroup_id: UUID, user: CueuserAuth = Depends(get_current_user)):
    try:
        ngroup = await get_ngroup(ngroup_id)
        return ngroup
    except NgroupNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{ngroup_id}", response_model=NgroupReturn)
async def update_ngroup_endpoint(ngroup_id: UUID, ngroup_update: NgroupUpdate, user: CueuserAuth = Depends(get_current_user)):
    try:
        updated_ngroup = await update_ngroup(ngroup_id, ngroup_update)
        return updated_ngroup
    except NgroupNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{ngroup_id}", response_model=bool)
async def delete_ngroup_endpoint(ngroup_id: UUID, user: CueuserAuth = Depends(get_current_user)):
    try:
        success = await delete_ngroup(ngroup_id)
        return success
    except NgroupNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[NgroupReturn])
async def list_ngroups_endpoint(user: CueuserAuth = Depends(get_current_user)):
    return await list_ngroups()

