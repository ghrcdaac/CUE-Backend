# ==============================================================================
# File: src/python/api/v2/endpoints/egress.py (Corrected)
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, Query
from uuid import UUID
from typing import List, Optional

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser
from v2.utils import egress as egress_utils
from v2.type_util.egress import EgressCreate, EgressUpdate, EgressResponse, PaginatedEgressResponse

router = APIRouter(prefix="/egress", tags=["V2 - DAAC Egress"])

@router.post("/", response_model=EgressResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_privilege("egress:create"))])
async def create_egress_endpoint(
    request: Request, 
    egress: EgressCreate, 
    user: AuthUser = Depends(get_current_user)
):
    """Creates a new egress target within the user's active ngroup."""
    if not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")
    
    ngroup_id = UUID(user.active_ngroup_id)
    try:
        new_egress = await egress_utils.create_egress(request, egress, ngroup_id)
        return EgressResponse.model_validate(new_egress)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=PaginatedEgressResponse, dependencies=[Depends(require_privilege("egress:read"))])
async def list_egresses_endpoint(
    request: Request, 
    user: AuthUser = Depends(get_current_user),
    # Read the active ngroup ID directly from the header
    active_ngroup_id: Optional[str] = Header(None, alias="x-active-ngroup-id"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=50)
):
    """Retrieves all egress records, filtered by the user's active ngroup from the header."""
    try:
        # Pass the header value and the user object to the utility function
        return await egress_utils.list_egresses(request, user, active_ngroup_id,page, page_size)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{egress_id}", response_model=EgressResponse, dependencies=[Depends(require_privilege("egress:read"))])
async def get_egress_endpoint(request: Request, egress_id: UUID, user: AuthUser = Depends(get_current_user)):
    """Retrieves a single egress target by its ID."""
    try:
        egress = await egress_utils.get_egress(request, egress_id)
        is_admin = "admin" in user.roles
        
        # ---  Check against the user's ACTIVE ngroup_id ---
        if not is_admin:
            if not user.active_ngroup_id:
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required for this action.")
            if str(egress['ngroup_id']) != user.active_ngroup_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
            
        return EgressResponse.model_validate(egress)
    except egress_utils.EgressNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.patch("/{egress_id}", response_model=EgressResponse, dependencies=[Depends(require_privilege("egress:update"))])
async def update_egress_endpoint(
    request: Request, 
    egress_id: UUID, 
    egress_update: EgressUpdate, 
    user: AuthUser = Depends(get_current_user)
):
    """Updates an existing egress target."""
    try:
        egress_to_update = await egress_utils.get_egress(request, egress_id)
        is_admin = "admin" in user.roles
        
        # ---  Check against the user's ACTIVE ngroup_id ---
        if not is_admin:
            if not user.active_ngroup_id:
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required for this action.")
            if str(egress_to_update['ngroup_id']) != user.active_ngroup_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        
        updated_egress = await egress_utils.update_egress(request, egress_id, egress_update)
        return EgressResponse.model_validate(updated_egress)
    except egress_utils.EgressNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{egress_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_privilege("egress:delete"))])
async def delete_egress_endpoint(request: Request, egress_id: UUID, user: AuthUser = Depends(get_current_user)):
    """Deletes an egress target."""
    try:
        egress_to_delete = await egress_utils.get_egress(request, egress_id)
        is_admin = "admin" in user.roles
        
        # ---  Check against the user's ACTIVE ngroup_id ---
        if not is_admin:
            if not user.active_ngroup_id:
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required for this action.")
            if str(egress_to_delete['ngroup_id']) != user.active_ngroup_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        await egress_utils.delete_egress(request, egress_id)
    except egress_utils.EgressNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))