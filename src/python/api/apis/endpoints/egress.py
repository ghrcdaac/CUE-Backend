from fastapi import APIRouter, HTTPException, Depends, Query
from uuid import UUID
from typing import List
import logging

from utils.egress import (create_egress, get_egress, update_egress,
                          list_egresses, delete_egress, EgressNotFoundError)
from lambda_utils.type_util.egress import EgressCreate, EgressReturn, EgressUpdate
from utils.auth import get_cognito_auth  # Import authentication

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/egress", tags=["egress"])


@router.post("/", response_model=EgressReturn)
async def create_egress_endpoint(
    egress: EgressCreate,
    current_user: dict = Depends(get_cognito_auth().get_current_user)  # Require auth
):
    """Creates a new egress record (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return await create_egress(egress)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{egress_id}", response_model=EgressReturn)
async def get_egress_endpoint(
    egress_id: UUID,
    ngroup_id: UUID = Query(..., description="ngroup ID for filtering"), # Add ngroup_id
    current_user: dict = Depends(get_cognito_auth().get_current_user)  # Require auth
):
    """Retrieves an egress record by its ID, filtered by ngroup_id (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        egress = await get_egress(egress_id, ngroup_id) # Pass ngroup
        if egress is None:
             raise EgressNotFoundError(egress_id=egress_id, ngroup_id=ngroup_id)
        return egress
    except EgressNotFoundError as e:  # Catch custom exception
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[EgressReturn])
async def list_egresses_endpoint(
    ngroup_id: UUID = Query(..., description="ngroup ID for filtering"),  # Add ngroup_id
    current_user: dict = Depends(get_cognito_auth().get_current_user)  # Require auth
):
    """Retrieves all egress records, filtered by ngroup_id (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        egress_list = await list_egresses(ngroup_id) #Pass ngroup
        logger.info(f"Egress list returned: {egress_list}")
        return egress_list
    except ValueError as e:
        logger.error(f"Error listing egresses: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{egress_id}", response_model=EgressReturn)
async def update_egress_endpoint(
    egress_id: UUID,
    egress_update: EgressUpdate,
    current_user: dict = Depends(get_cognito_auth().get_current_user)  # Require auth
):
    """Updates an existing egress record (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        updated_egress = await update_egress(egress_id, egress_update)
        if updated_egress is None:
            raise HTTPException(status_code=404, detail="Egress not found")
        return updated_egress
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{egress_id}", response_model=bool)
async def delete_egress_endpoint(
    egress_id: UUID,
    ngroup_id: UUID = Query(..., description="ngroup ID for filtering"), # Add ngroup_id
    current_user: dict = Depends(get_cognito_auth().get_current_user)  # Require auth
):
    """Deletes an egress record by its ID, filtered by ngroup_id (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        success = await delete_egress(egress_id, ngroup_id) # Pass ngroup
        if not success:
            raise EgressNotFoundError(egress_id=egress_id, ngroup_id=ngroup_id)
        return success
    except EgressNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))