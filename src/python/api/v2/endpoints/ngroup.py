from fastapi import APIRouter, HTTPException, Query, Depends, status
from uuid import UUID
from typing import List, Optional, Dict, Any

from v2.utils.ngroup import create_ngroup, get_ngroup_id_by_name, get_ngroup, update_ngroup, delete_ngroup, list_ngroups, NgroupNotFoundError  
from lambda_utils.type_util.ngroup import NgroupCreate, NgroupReturn, NgroupUpdate

from v2.utils.JWTBearer import bearer_scheme, JWTBearer  # Import the dependency
from v2.utils.auth import get_cognito_auth, CognitoAuth


router = APIRouter(prefix="/ngroup", tags=["ngroup"])

@router.post("/", response_model=NgroupReturn)
async def create_ngroup_endpoint(
    ngroup: NgroupCreate,
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return await create_ngroup(ngroup)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

@router.get("/id", response_model=UUID)
async def get_ngroup_id_endpoint(
    short_name: Optional[str] = Query(None, alias="short_name"),
    long_name: Optional[str] = Query(None, alias="long_name"),
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)

):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        ngroup_id = await get_ngroup_id_by_name(short_name, long_name)
        return ngroup_id
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NgroupNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e: #Catch exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e

@router.get("/{ngroup_id}", response_model=NgroupReturn)
async def get_ngroup_endpoint(
    ngroup_id: UUID,
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        ngroup = await get_ngroup(ngroup_id)
        return ngroup
    except NgroupNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e: #Catch exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e

@router.patch("/{ngroup_id}", response_model=NgroupReturn)
async def update_ngroup_endpoint(
    ngroup_id: UUID,
    ngroup_update: NgroupUpdate,
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        updated_ngroup = await update_ngroup(ngroup_id, ngroup_update)
        return updated_ngroup
    except NgroupNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:  # Catch validation errors from Pydantic
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e: #Catch exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e

@router.delete("/{ngroup_id}", response_model=bool)
async def delete_ngroup_endpoint(
    ngroup_id: UUID,
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        success = await delete_ngroup(ngroup_id)
        return success
    except NgroupNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e: #Catch exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e

@router.get("/", response_model=List[NgroupReturn])
async def list_ngroups_endpoint(current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return await list_ngroups()
    except Exception as e: #Catch exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e