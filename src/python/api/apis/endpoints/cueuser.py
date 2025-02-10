from fastapi import APIRouter, HTTPException, Query, Depends
from uuid import UUID
from typing import List, Optional

from utils.cueuser import create_cueuser, get_cueuser, update_cueuser, delete_cueuser, list_cueusers, CueuserNotFoundError, get_cueuser_by_lookup
from lambda_utils.type_util.cueuser import CueuserCreate, CueuserReturn, CueuserUpdate
from lambda_utils.type_util.cueuser import CueuserAuth
from utils.auth import get_current_user

router = APIRouter(prefix="/cueuser", tags=["cueuser"])

@router.post("/", response_model=CueuserReturn)
async def create_cueuser_endpoint(cueuser: CueuserCreate, user: CueuserAuth = Depends(get_current_user)):
    try:
        return await create_cueuser(cueuser)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/find", response_model=CueuserReturn)
async def lookup_cueuser_endpoint(
    email: Optional[str] = Query(None, description="Email to search for"),
    cueusername: Optional[str] = Query(None, description="Username to search for"),
    name: Optional[str] = Query(None, description="Name to search for"),
    edpub_id: Optional[str] = Query(None, description="Edpub ID to search for"),
    user: CueuserAuth = Depends(get_current_user)
):
    try:
        cueuser = await get_cueuser_by_lookup(email, cueusername, name, edpub_id)
        return cueuser
    except CueuserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{cueuser_id}", response_model=CueuserReturn)
async def get_cueuser_endpoint(cueuser_id: UUID, user: CueuserAuth = Depends(get_current_user)):
    try:
        cueuser = await get_cueuser(cueuser_id)
        return cueuser
    except CueuserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{cueuser_id}", response_model=CueuserReturn)
async def update_cueuser_endpoint(cueuser_id: UUID, cueuser_update: CueuserUpdate, user: CueuserAuth = Depends(get_current_user)):
    try:
        updated_cueuser = await update_cueuser(cueuser_id, cueuser_update)
        return updated_cueuser
    except CueuserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{cueuser_id}", response_model=bool)
async def delete_cueuser_endpoint(cueuser_id: UUID, user: CueuserAuth = Depends(get_current_user)):
    try:
        success = await delete_cueuser(cueuser_id)
        return success
    except CueuserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[CueuserReturn])
async def list_cueusers_endpoint(user: CueuserAuth = Depends(get_current_user)):
    try:
        return await list_cueusers()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
