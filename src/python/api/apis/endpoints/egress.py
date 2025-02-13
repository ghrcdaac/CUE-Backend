from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from typing import List
import logging

from utils.egress import create_egress, get_egress, update_egress, list_egresses, delete_egress
from lambda_utils.type_util.egress import EgressCreate, EgressReturn, EgressUpdate
from lambda_utils.type_util.cueuser import CueuserAuth
from utils.auth import get_current_user, auth_scheme

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/egress", tags=["egress"])


@router.post("/", response_model=EgressReturn)
async def create_egress_endpoint(egress: EgressCreate, user: CueuserAuth = Depends(auth_scheme)):
    try:
        return await create_egress(egress)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{egress_id}", response_model=EgressReturn)
async def get_egress_endpoint(egress_id: UUID, user: CueuserAuth = Depends(get_current_user)):
    try:
        egress = await get_egress(egress_id)
        if egress is None:
            raise HTTPException(status_code=404, detail="Egress not found")
        return egress
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[EgressReturn])
async def list_egresses_endpoint(user: CueuserAuth = Depends(get_current_user)):
    try:
        egress_list = await list_egresses()

        # Log the data being returned
        logger.info(f"Egress list returned from database: {egress_list}")

        return egress_list
    except ValueError as e:
        logger.error(f"Error listing egresses: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{egress_id}", response_model=EgressReturn)
async def update_egress_endpoint(egress_id: UUID, egress_update: EgressUpdate, user: CueuserAuth = Depends(get_current_user)):
    try:
        updated_egress = await update_egress(egress_id, egress_update)
        if updated_egress is None:
            raise HTTPException(status_code=404, detail="Egress not found")
        return updated_egress
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{egress_id}", response_model=bool)
async def delete_egress_endpoint(egress_id: UUID, user: CueuserAuth = Depends(get_current_user)):
    try:
        success = await delete_egress(egress_id)
        if not success:
            raise HTTPException(status_code=404, detail="Egress not found or could not be deleted")
        return success
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
