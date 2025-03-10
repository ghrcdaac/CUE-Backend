# endpoints/provider.py (Modified)
from fastapi import APIRouter, HTTPException, Query, Depends, status
from uuid import UUID
from typing import List, Optional, Dict, Any  # Import Dict and Any

from utils.provider import create_provider, get_provider, update_provider, delete_provider, list_providers, ProviderNotFoundError, get_provider_by_lookup
from lambda_utils.type_util.provider import ProviderCreate, ProviderReturn, ProviderUpdate

from utils.JWTBearer import bearer_scheme, JWTBearer  # Import for authentication
from utils.auth import get_cognito_auth, CognitoAuth


router = APIRouter(prefix="/provider", tags=["provider"])

@router.post("/", response_model=ProviderReturn)
async def create_provider_endpoint(
    provider: ProviderCreate,
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return await create_provider(provider)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/find", response_model=ProviderReturn)
async def lookup_provider_endpoint(
    short_name: Optional[str] = Query(None, description="Provider Short Name to search for"),
    long_name: Optional[str] = Query(None, description="Provider Long Name to search for"),
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        provider = await get_provider_by_lookup(short_name, long_name)
        return provider
    except ProviderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))



@router.get("/{provider_id}", response_model=ProviderReturn)
async def get_provider_endpoint(
    provider_id: UUID,
    ngroup_id: Optional[UUID] = Query(None, description="Filter by ngroup ID"),
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        provider = await get_provider(provider_id, ngroup_id)
        return provider
    except ProviderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/{provider_id}", response_model=ProviderReturn)
async def update_provider_endpoint(
    provider_id: UUID,
    provider_update: ProviderUpdate,
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        updated_provider = await update_provider(provider_id, provider_update)
        return updated_provider
    except ProviderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{provider_id}", response_model=bool)
async def delete_provider_endpoint(
    provider_id: UUID,
    ngroup_id: Optional[UUID] = Query(None, description="Filter by ngroup ID"),
    current_user: dict = Depends(get_cognito_auth().get_current_user),
    token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        success = await delete_provider(provider_id, ngroup_id)
        return success
    except ProviderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=List[ProviderReturn])
async def list_providers_endpoint(
        ngroup_id: Optional[UUID] = Query(None, description="Filter by ngroup ID"),
        can_upload: Optional[bool] = Query(None, description="Filter by can_upload status"),
        current_user: dict = Depends(get_cognito_auth().get_current_user),
        token: str = Depends(bearer_scheme)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return await list_providers(ngroup_id, can_upload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))