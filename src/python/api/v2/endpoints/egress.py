# File: src/python/api/v2/endpoints/egress.py

from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser
from v2.utils import egress as egress_utils
from v2.type_util.egress import EgressCreate, EgressUpdate, EgressResponse

router = APIRouter(prefix="/egress", tags=["V2 - Egress Targets"])

@router.post("/", response_model=EgressResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_privilege("egress:create"))])
async def create_egress_endpoint(egress: EgressCreate, user: AuthUser = Depends(get_current_user)):
    """Creates a new egress target within the user's active ngroup."""
    if "admin" not in user.roles and not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")
    
    ngroup_id = UUID(user.active_ngroup_id)
    try:
        new_egress = await egress_utils.create_egress(egress, ngroup_id)
        return EgressResponse.model_validate(new_egress)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=List[EgressResponse], dependencies=[Depends(require_privilege("egress:read"))])
async def list_egresses_endpoint(user: AuthUser = Depends(get_current_user)):
    """Retrieves all egress records for the user's active ngroup."""
    if "admin" not in user.roles and not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")

    ngroup_id = UUID(user.active_ngroup_id)
    try:
        return await egress_utils.list_egresses(ngroup_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{egress_id}", response_model=EgressResponse, dependencies=[Depends(require_privilege("egress:read"))])
async def get_egress_endpoint(egress_id: UUID, user: AuthUser = Depends(get_current_user)):
    """Retrieves a single egress target by its ID."""
    try:
        egress = await egress_utils.get_egress(egress_id)
        if "admin" not in user.roles and str(egress['ngroup_id']) not in user.ngroups:
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        return EgressResponse.model_validate(egress)
    except egress_utils.EgressNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/{egress_id}", response_model=EgressResponse, dependencies=[Depends(require_privilege("egress:update"))])
async def update_egress_endpoint(egress_id: UUID, egress_update: EgressUpdate, user: AuthUser = Depends(get_current_user)):
    """Updates an existing egress target."""
    try:
        # First, ensure the user has access to this egress target
        egress_to_update = await egress_utils.get_egress(egress_id)
        if "admin" not in user.roles and str(egress_to_update['ngroup_id']) not in user.ngroups:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        
        # If access is confirmed, perform the update
        updated_egress = await egress_utils.update_egress(egress_id, egress_update)
        return EgressResponse.model_validate(updated_egress)
    except egress_utils.EgressNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{egress_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_privilege("egress:delete"))])
async def delete_egress_endpoint(egress_id: UUID, user: AuthUser = Depends(get_current_user)):
    """Deletes an egress target."""
    try:
        # First, ensure the user has access to this egress target
        egress_to_delete = await egress_utils.get_egress(egress_id)
        if "admin" not in user.roles and str(egress_to_delete['ngroup_id']) not in user.ngroups:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        # If access is confirmed, perform the delete
        await egress_utils.delete_egress(egress_id)
    except egress_utils.EgressNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))