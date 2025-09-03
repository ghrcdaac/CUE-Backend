from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser
from v2.utils import api_keys as api_key_utils
from v2.type_util.api_keys import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyInfo, ApiKeyUpdateRequest

router = APIRouter(prefix="/api-keys", tags=["V2 - API Keys"])

@router.post("/", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_privilege("api-key:create"))])
async def create_api_key_endpoint(request: ApiKeyCreateRequest, user: AuthUser = Depends(get_current_user)):
    """Creates a new API key, either for the requester or a target user/proxy."""
    try:
        created_key = await api_key_utils.create_api_key(request, user)
        return ApiKeyCreateResponse.model_validate(created_key)
    except (ValueError, api_key_utils.ApiKeyPermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=List[ApiKeyInfo], dependencies=[Depends(require_privilege("api-key:read"))])
async def list_api_keys_endpoint(user: AuthUser = Depends(get_current_user)):
    """
    Lists API keys.
    - Regular users see keys created by or for them.
    - Managers/Admins see all keys within their active ngroup.
    """
    try:
        return await api_key_utils.list_api_keys(user)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/{key_id}", status_code=status.HTTP_204_NO_CONTENT,
              dependencies=[Depends(require_privilege("api-key:update"))])
async def update_api_key_endpoint(key_id: UUID, request: ApiKeyUpdateRequest, user: AuthUser = Depends(get_current_user)):
    """Updates an API key (e.g., suspends or reactivates it)."""
    try:
        await api_key_utils.update_api_key(key_id, request, user)
    except api_key_utils.ApiKeyNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except api_key_utils.ApiKeyPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/{key_id}/record-usage", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=[Depends(require_privilege("file:upload"))]) # Protected by a basic privilege
async def record_key_usage_endpoint(key_id: UUID):
    """
    An internal-facing endpoint to update the `last_used_at` timestamp of an API key.
    This should be called by other services (like the Upload API) upon successful key usage.
    """
    try:
        await api_key_utils.record_api_key_usage(key_id)
    except Exception:
        # Silently fail or log. This operation is not critical to the user-facing flow.
        pass


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_privilege("api-key:delete"))])
async def revoke_api_key_endpoint(key_id: UUID, user: AuthUser = Depends(get_current_user)):
    """Revokes (deletes) an API key."""
    try:
        await api_key_utils.revoke_api_key(key_id, user)
    except api_key_utils.ApiKeyNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except api_key_utils.ApiKeyPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
