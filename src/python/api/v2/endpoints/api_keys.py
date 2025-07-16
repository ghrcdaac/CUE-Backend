# ==============================================================================
# File: src/python/api/v2/endpoints/api_keys.py (New)
# Purpose: Provides the REST API endpoints for managing API keys.
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List

from core.security import get_current_user, User
from ..utils import api_keys as api_key_utils
from ..type_util.api_keys import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyInfo

router = APIRouter(prefix="/api-keys", tags=["V2 - API Keys"])

@router.get("/", response_model=List[ApiKeyInfo])
async def get_my_api_keys(user: User = Depends(get_current_user)):
    """
    Lists all API keys for the currently authenticated user.
    The secret key itself is not returned.
    """
    return await api_key_utils.list_user_api_keys(user.id)

@router.post("/", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: ApiKeyCreateRequest,
    user: User = Depends(get_current_user)
):
    """
    Creates a new API key for the currently authenticated user.
    The secret key is only returned in this response.
    """
    created_key = await api_key_utils.create_api_key_for_user(user.id, request.name)
    return ApiKeyCreateResponse(**created_key)

@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key_endpoint(
    key_id: UUID,
    user: User = Depends(get_current_user)
):
    """
    Revokes (deletes) an API key owned by the currently authenticated user.
    """
    try:
        await api_key_utils.revoke_user_api_key(key_id, user.id)
    except api_key_utils.ApiKeyNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
