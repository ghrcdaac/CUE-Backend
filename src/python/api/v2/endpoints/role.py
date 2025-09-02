# ==============================================================================
# File: src/python/api/v2/endpoints/role.py (Final)
# Purpose: Provides the v2 REST API endpoints for role management.
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from typing import List, Optional

from core.security import require_privilege
from v2.utils import role as role_utils
from v2.type_util.role import RoleCreate, RoleUpdate, RoleResponse

router = APIRouter(prefix="/roles", tags=["V2 - Roles"])

@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_privilege("role:create"))])
async def create_role_endpoint(role: RoleCreate):
    """Creates a new role. Requires 'admin' privilege."""
    try:
        new_role = await role_utils.create_role(role)
        return RoleResponse.model_validate(new_role)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.get("/", response_model=List[RoleResponse], dependencies=[Depends(require_privilege("role:read"))])
async def list_roles_endpoint():
    """Retrieves all role records. Requires 'admin' privilege."""
    try:
        return await role_utils.list_roles()
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.get("/find", response_model=RoleResponse, dependencies=[Depends(require_privilege("role:read"))])
async def lookup_role_endpoint(
    short_name: Optional[str] = Query(None, description="Role Short Name to search for"),
    long_name: Optional[str] = Query(None, description="Role Long Name to search for")
):
    """Finds a role by its short or long name. Requires 'admin' privilege."""
    try:
        role = await role_utils.get_role_by_lookup(short_name, long_name)
        return RoleResponse.model_validate(role)
    except role_utils.RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{role_id}", response_model=RoleResponse, dependencies=[Depends(require_privilege("role:read"))])
async def get_role_endpoint(role_id: UUID):
    """Retrieves a single role by its ID. Requires 'admin' privilege."""
    try:
        role = await role_utils.get_role(role_id)
        return RoleResponse.model_validate(role)
    except role_utils.RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.patch("/{role_id}", response_model=RoleResponse, dependencies=[Depends(require_privilege("role:update"))])
async def update_role_endpoint(role_id: UUID, role_update: RoleUpdate):
    """Updates an existing role. Requires 'admin' privilege."""
    try:
        updated_role = await role_utils.update_role(role_id, role_update)
        return RoleResponse.model_validate(updated_role)
    except role_utils.RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_privilege("role:delete"))])
async def delete_role_endpoint(role_id: UUID):
    """Deletes a role. Requires 'admin' privilege."""
    try:
        await role_utils.delete_role(role_id)
    except role_utils.RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
