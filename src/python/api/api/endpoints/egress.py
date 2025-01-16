from fastapi import APIRouter, HTTPException
from uuid import UUID
from typing import List

from lambda_utils.utils.egress import create_egress, get_egress, update_egress, list_egresses
from lambda_utils.type_util.egress import EgressCreate, EgressReturn, EgressUpdate

router = APIRouter(prefix="/egress", tags=["egress"])

@router.post("/", response_model=EgressReturn)
async def create_egress_endpoint(egress: EgressCreate):
    return await create_egress(egress)

@router.get("/{egress_id}", response_model=EgressReturn)
async def get_egress_endpoint(egress_id: UUID):
    egress = await get_egress(egress_id)
    if egress is None:
        raise HTTPException(status_code=404, detail="Egress not found")
    return egress

@router.get("/", response_model=List[EgressReturn])
async def list_egresses_endpoint():
    return await list_egresses()

@router.patch("/{egress_id}", response_model=EgressReturn)
async def update_egress_endpoint(egress_id: UUID, egress_update: EgressUpdate):
    updated_egress = await update_egress(egress_id, egress_update)
    if updated_egress is None:
        raise HTTPException(status_code=404, detail="Egress not found")
    return updated_egress