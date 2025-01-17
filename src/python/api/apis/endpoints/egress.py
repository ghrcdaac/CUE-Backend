from fastapi import APIRouter, HTTPException
from uuid import UUID
from typing import List

from utils.egress import create_egress, get_egress, update_egress, list_egresses, delete_egress
from lambda_utils.type_util.egress import EgressCreate, EgressReturn, EgressUpdate

router = APIRouter(prefix="/egress", tags=["egress"])

@router.post("/", response_model=EgressReturn)
async def create_egress_endpoint(egress: EgressCreate):
    try:
        return await create_egress(egress)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{egress_id}", response_model=EgressReturn)
async def get_egress_endpoint(egress_id: UUID):
    try:
        egress = await get_egress(egress_id)
        if egress is None:
            raise HTTPException(status_code=404, detail="Egress not found")
        return egress
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[EgressReturn])
async def list_egresses_endpoint():
    try:
        return await list_egresses()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{egress_id}", response_model=EgressReturn)
async def update_egress_endpoint(egress_id: UUID, egress_update: EgressUpdate):
    try:
        updated_egress = await update_egress(egress_id, egress_update)
        if updated_egress is None:
            raise HTTPException(status_code=404, detail="Egress not found")
        return updated_egress
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{egress_id}", response_model=bool)
async def delete_egress_endpoint(egress_id: UUID):
    try:
        success = await delete_egress(egress_id)
        if not success:
            raise HTTPException(status_code=404, detail="Egress not found or could not be deleted")
        return success
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))