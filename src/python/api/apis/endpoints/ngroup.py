from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from typing import List, Optional

from utils.ngroup import create_ngroup, get_ngroup_id_by_name
from lambda_utils.type_util.ngroup import NgroupCreate, NgroupReturn

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