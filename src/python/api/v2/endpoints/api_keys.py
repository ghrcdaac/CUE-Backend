# ==============================================================================
# File: src/python/api/v2/endpoints/api_keys.py
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, Query
from uuid import UUID
from typing import List, Optional

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser
from v2.utils import api_keys as api_key_utils
from v2.type_util.api_keys import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyUpdateRequest, PaginatedAPIKeyResponse

router = APIRouter(prefix="/api-keys", tags=["V2 - API Keys"])

@router.post("/", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_privilege("api-key:create"))])
# Accepts the 'request' object
async def create_api_key_endpoint(fastapi_request: Request, request_body: ApiKeyCreateRequest, user: AuthUser = Depends(get_current_user)):
    """Creates a new API key, either for the requester or a target user/proxy."""
    try:
        # Passes the 'request' object to the util function
        created_key = await api_key_utils.create_api_key(fastapi_request, request_body, user)
        return ApiKeyCreateResponse.model_validate(created_key)
    except (ValueError, api_key_utils.ApiKeyPermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=PaginatedAPIKeyResponse, dependencies=[Depends(require_privilege("api-key:read"))])
async def list_api_keys_endpoint(
    request: Request, 
    user: AuthUser = Depends(get_current_user),
    # 1. This line reads the active DAAC/group ID from the HTTP header.
    active_ngroup_id: Optional[str] = Header(None, alias="x-active-ngroup-id"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    Lists API keys filtered by the user's active DAAC/ngroup.
    The active_ngroup_id is passed via the 'x-active-ngroup-id' header.
    """
    try:
        # 2. The active_ngroup_id is now passed down to the business logic layer.
        return await api_key_utils.list_api_keys(request, user, page, page_size, active_ngroup_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/{key_id}", status_code=status.HTTP_204_NO_CONTENT,
              dependencies=[Depends(require_privilege("api-key:update"))])
# Renamed 'request' to avoid conflict and accept the FastAPI Request object
async def update_api_key_endpoint(request: Request, key_id: UUID, update_body: ApiKeyUpdateRequest, user: AuthUser = Depends(get_current_user)):
    """Updates an API key (e.g., suspends or reactivates it)."""
    try:
        # Passes the 'request' object to the util function
        await api_key_utils.update_api_key(request, key_id, update_body, user)
    except api_key_utils.ApiKeyNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except api_key_utils.ApiKeyPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/{key_id}/record-usage", status_code=status.HTTP_204_NO_CONTENT,
              dependencies=[Depends(require_privilege("file:upload"))]) # Protected by a basic privilege
# Accepts the 'request' object
async def record_key_usage_endpoint(request: Request, key_id: UUID):
    """
    An internal-facing endpoint to update the `last_used_at` timestamp of an API key.
    This should be called by other services (like the Upload API) upon successful key usage.
    """
    try:
        # Passes the 'request' object to the util function
        await api_key_utils.record_api_key_usage(request, key_id)
    except Exception:
        # Silently fail or log. This operation is not critical to the user-facing flow.
        pass

@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_privilege("api-key:delete"))])
# Accepts the 'request' object
async def revoke_api_key_endpoint(request: Request, key_id: UUID, user: AuthUser = Depends(get_current_user)):
    """Revokes (deletes) an API key."""
    try:
        # Passes the 'request' object to the util function
        await api_key_utils.revoke_api_key(request, key_id, user)
    except api_key_utils.ApiKeyNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except api_key_utils.ApiKeyPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))