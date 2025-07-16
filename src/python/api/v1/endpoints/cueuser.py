from fastapi import APIRouter, HTTPException, Query, Depends, status, Response
from uuid import UUID
from typing import List, Optional

from v1.utils.cueuser import (create_cueuser, get_cueuser, update_cueuser,
                           delete_cueuser, list_cueusers,
                           CueuserNotFoundError, get_cueuser_by_lookup,
                           get_cueuser_role, get_cognito_client, get_cueuser_by_username_util)
from lambda_utils.type_util.cueuser import (CueuserCreate, CueuserReturn,
                                           CueuserUpdate, CueuserRoleReturn)
from v1.utils.JWTBearer import bearer_scheme  # Import JWTBearer
from v1.utils.auth import get_cognito_auth

router = APIRouter(prefix="/cueuser", tags=["cueuser"])


@router.post("/", response_model=CueuserReturn, status_code=status.HTTP_201_CREATED)
async def create_cueuser_endpoint(cueuser: CueuserCreate,
                                  cognito_client=Depends(get_cognito_client),
                                  current_user: dict = Depends(get_cognito_auth().get_current_user),
                                  token: str = Depends(bearer_scheme)
                                 ):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return await create_cueuser(cueuser, cognito_client)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/find", response_model=CueuserReturn)
async def lookup_cueuser_endpoint(
        ngroup_id: UUID = Query(..., description="ngroup ID to filter"),
        email: Optional[str] = Query(None, description="Email to search for"),
        cueusername: Optional[str] = Query(None, description="Username to search for"),
        name: Optional[str] = Query(None, description="Name to search for"),
        edpub_id: Optional[str] = Query(None, description="Edpub ID to search for"),
        current_user: dict = Depends(get_cognito_auth().get_current_user),
        token: str = Depends(bearer_scheme)

):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        cueuser = await get_cueuser_by_lookup(ngroup_id, email, cueusername, name, edpub_id)
        return cueuser
    except CueuserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{cueuser_id}", response_model=CueuserReturn)
async def get_cueuser_endpoint(cueuser_id: UUID,
                               ngroup_id: UUID = Query(..., description="ngroup ID to filter"),
                               current_user: dict = Depends(get_cognito_auth().get_current_user),
                               token: str = Depends(bearer_scheme)
                               ):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        cueuser = await get_cueuser(cueuser_id, ngroup_id)
        return cueuser
    except CueuserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/{cueuser_id}", response_model=CueuserReturn)
async def update_cueuser_endpoint(cueuser_id: UUID,
                                  cueuser_update: CueuserUpdate,
                                  current_user: dict = Depends(get_cognito_auth().get_current_user),
                                  token: str = Depends(bearer_scheme)
                                  ):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        updated_cueuser = await update_cueuser(cueuser_id, cueuser_update)
        return updated_cueuser
    except CueuserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{cueuser_id}/role", response_model=CueuserRoleReturn)  # updated
async def get_cueuser_role_endpoint(cueuser_id: UUID,
                                    current_user: dict = Depends(get_cognito_auth().get_current_user),
                                    token: str = Depends(bearer_scheme)
                                    ):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        return await get_cueuser_role(cueuser_id)
    except CueuserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{cueuser_id}", response_model=bool)
async def delete_cueuser_endpoint(cueuser_id: UUID,
                                  ngroup_id: UUID = Query(...),
                                  cognito_client=Depends(get_cognito_client),
                                  current_user: dict = Depends(get_cognito_auth().get_current_user),
                                  token: str = Depends(bearer_scheme)
                                  ):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        success = await delete_cueuser(cueuser_id, ngroup_id, cognito_client)
        return success
    except CueuserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=List[CueuserReturn])
async def list_cueusers_endpoint(ngroup_id: UUID = Query(..., description="ngroup ID to filter"),
                                 current_user: dict = Depends(get_cognito_auth().get_current_user),
                                 token: str = Depends(bearer_scheme)
                                 ):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return await list_cueusers(ngroup_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:  # Catch other exceptions.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
@router.get("/by_username/{username}", response_model=CueuserReturn)
async def get_cueuser_by_username_endpoint(
    username: str,
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    """Retrieves a cueuser by their username."""

    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        return await get_cueuser_by_username_util(username)  # Call the utility function
    except CueuserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))