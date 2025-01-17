from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from typing import List, Optional

from utils.ngroup import create_ngroup, get_ngroup_id_by_name, get_ngroup, update_ngroup, delete_ngroup, list_ngroups
from lambda_utils.type_util.ngroup import NgroupCreate, NgroupReturn, NgroupUpdate

router = APIRouter(prefix="/ngroup", tags=["ngroup"])

@router.post("/", response_model=NgroupReturn)
async def create_ngroup_endpoint(ngroup: NgroupCreate):
    return await create_ngroup(ngroup)

@router.get("/id", response_model=UUID)
async def get_ngroup_id_endpoint(
    short_name: Optional[str] = Query(None, alias="short_name"),
    long_name: Optional[str] = Query(None, alias="long_name")
):
    ngroup_id = await get_ngroup_id_by_name(short_name, long_name)
    if ngroup_id is None:
        raise HTTPException(status_code=404, detail="Ngroup not found")
    return ngroup_id

@router.get("/{ngroup_id}", response_model=NgroupReturn)
async def get_ngroup_endpoint(ngroup_id: UUID):
    ngroup = await get_ngroup(ngroup_id)
    if ngroup is None:
        raise HTTPException(status_code=404, detail="Ngroup not found")
    return ngroup

@router.patch("/{ngroup_id}", response_model=NgroupReturn)
async def update_ngroup_endpoint(ngroup_id: UUID, ngroup_update: NgroupUpdate):
    updated_ngroup = await update_ngroup(ngroup_id, ngroup_update)
    if updated_ngroup is None:
        raise HTTPException(status_code=404, detail="Ngroup not found")
    return updated_ngroup

@router.delete("/{ngroup_id}", response_model=bool)
async def delete_ngroup_endpoint(ngroup_id: UUID):
    success = await delete_ngroup(ngroup_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ngroup not found or could not be deleted")
    return success

@router.get("/", response_model=List[NgroupReturn])
async def list_ngroups_endpoint():
    return await list_ngroups()