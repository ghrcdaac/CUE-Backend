# ==============================================================================
# File: src/python/api/v2/endpoints/ngroup.py (Updated)
# --- MODIFIED to pass the request object down to the utility layer ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Request # <-- Import Request
from uuid import UUID
from typing import List

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser as User
from v2.utils import ngroup as ngroup_utils
from v2.type_util.ngroup import NgroupCreate, NgroupUpdate, NgroupResponse, NgroupListResponse

router = APIRouter(prefix="/ngroups", tags=["V2 - NGroups"])

# --- MODIFIED: All endpoints now accept `request: Request` ---

@router.post("/", response_model=NgroupResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_privilege("admin"))])
async def create_ngroup_endpoint(request: Request, ngroup: NgroupCreate):
    """Creates a new ngroup. Requires 'admin' privilege."""
    try:
        new_ngroup = await ngroup_utils.create_ngroup(request, ngroup)
        return NgroupResponse.model_validate(new_ngroup)
    except ValueError as e:
        # This catches bad requests, like duplicate names.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Catch-all for any other unexpected errors.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while creating the ngroup.")

@router.get("/for-application-form", response_model=List[NgroupListResponse])
async def list_ngroups_for_application_form(request: Request):
    """
    A public endpoint to retrieve a simplified list of ngroups.
    This is used to populate the dropdown in the user application form.
    """
    try:
        return await ngroup_utils.list_ngroups_for_form(request)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve ngroups for the application form.")

@router.get("/", response_model=List[NgroupResponse], dependencies=[Depends(get_current_user)])
async def list_ngroups_endpoint(request: Request):
    """Retrieves all ngroup records. Requires any authenticated user."""
    try:
        return await ngroup_utils.list_ngroups(request)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while listing ngroups.")

@router.get("/{ngroup_id}", response_model=NgroupResponse, dependencies=[Depends(get_current_user)])
async def get_ngroup_endpoint(request: Request, ngroup_id: UUID):
    """Retrieves a single ngroup by its ID."""
    try:
        ngroup = await ngroup_utils.get_ngroup(request, ngroup_id)
        return NgroupResponse.model_validate(ngroup)
    except ngroup_utils.NgroupNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while retrieving the ngroup.")

@router.patch("/{ngroup_id}", response_model=NgroupResponse, dependencies=[Depends(require_privilege("admin"))])
async def update_ngroup_endpoint(request: Request, ngroup_id: UUID, ngroup_update: NgroupUpdate):
    """Updates an existing ngroup. Requires 'admin' privilege."""
    try:
        updated_ngroup = await ngroup_utils.update_ngroup(request, ngroup_id, ngroup_update)
        return NgroupResponse.model_validate(updated_ngroup)
    except ngroup_utils.NgroupNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while updating the ngroup.")

@router.delete("/{ngroup_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_privilege("admin"))])
async def delete_ngroup_endpoint(request: Request, ngroup_id: UUID):
    """Deletes an ngroup. Requires 'admin' privilege."""
    try:
        await ngroup_utils.delete_ngroup(request, ngroup_id)
    except ngroup_utils.NgroupNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while deleting the ngroup.")
