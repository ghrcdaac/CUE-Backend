# endpoints/role.py (Modified)
from fastapi import APIRouter, HTTPException, Query, Depends, status
from uuid import UUID
from typing import List, Optional, Dict, Any  # Import Dict and Any

from v2.utils.role import create_role, get_role, update_role, delete_role, list_roles, get_role_by_lookup, RoleNotFoundError
from lambda_utils.type_util.role import RoleCreate, RoleReturn, RoleUpdate

from v2.utils.JWTBearer import bearer_scheme, JWTBearer  # Import for authentication
from v2.utils.auth import get_cognito_auth, CognitoAuth


router = APIRouter(prefix="/role", tags=["role"])

@router.post("/", response_model=RoleReturn)
async def create_role_endpoint(
    role: RoleCreate,
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return await create_role(role)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e: #Catch exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e

@router.get("/find", response_model=RoleReturn)
async def lookup_role_endpoint(
    short_name: Optional[str] = Query(None, description="Role Short Name to search for"),
    long_name: Optional[str] = Query(None, description="Role Long Name to search for"),
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        role = await get_role_by_lookup(short_name, long_name)
        return role
    except RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e: #Catch exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e

@router.get("/{role_id}", response_model=RoleReturn)
async def get_role_endpoint(
    role_id: UUID,
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        role = await get_role(role_id)
        return role
    except RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e: #Catch exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e

@router.patch("/{role_id}", response_model=RoleReturn)
async def update_role_endpoint(
    role_id: UUID,
    role_update: RoleUpdate,
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        updated_role = await update_role(role_id, role_update)
        return updated_role
    except RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e: #Catch exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e
@router.delete("/{role_id}", response_model=bool)
async def delete_role_endpoint(
    role_id: UUID,
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        success = await delete_role(role_id)
        return success
    except RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e: #Catch exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e

@router.get("/", response_model=List[RoleReturn])
async def list_roles_endpoint(
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return await list_roles()
    except Exception as e: #Catch exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e