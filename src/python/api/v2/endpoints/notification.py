# ==============================================================================
# File: src/python/api/v2/endpoints/provider.py (Corrected)
# --- MODIFIED to pass the request object to the utility layer ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Header
from uuid import UUID
from typing import List, Optional

from core.security import require_privilege, get_current_user
from v2.type_util.auth import AuthUser
from v2.utils import notification as notification_utils
from v2.type_util.notification import (
    NotificationResponse, Notification
)

router = APIRouter(prefix="/notification", tags=["V2 - Notification"])

@router.get("/user", response_model=List[NotificationResponse], dependencies=[Depends(require_privilege("metrics:read"))])
async def lookup_notification_by_user(
    request: Request,
    user: AuthUser = Depends(get_current_user)
):
    """Finds a notification based on user_id (requires authentication)."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        notifications = await notification_utils.list_notifications_by_user(request,user)
        return notifications
    except notification_utils.NotificationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"notification not found for user: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
@router.get("/{notification_id}", response_model=NotificationResponse, dependencies=[Depends(require_privilege("metrics:read"))])
async def get_notification_endpoint(request: Request, provider_id: UUID):
    """Retrieves notification by its ID"""
    try:
        notification = await notification_utils.get_notification(request, provider_id)
        return NotificationResponse.model_validate(notification)
    except notification_utils.NotificationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/", response_model=List[NotificationResponse], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_privilege("metrics:read"))])
async def add_notification_preference(request: Request, notifications: List[Notification], user: AuthUser = Depends(get_current_user)):
    """Creates a new notification"""
    try:
        return await notification_utils.create_notification(request, user, notifications)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/{notification_id}", response_model=NotificationResponse, dependencies=[Depends(require_privilege("provider:update"))])
async def update_provider_endpoint(request: Request, provider_id: UUID, provider_update: Notification):
    """Updates an existing provider. Requires 'provider:update' privilege."""
    try:
        updated_provider = await provider_utils.update_provider(request, provider_id, provider_update)
        return ProviderResponse.model_validate(updated_provider)
    except provider_utils.ProviderNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
# @router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_privilege("metrics:delete"))])
# async def delete_notification_endpoint(request: Request, provider_id: UUID):
#     """Deletes a notification. Requires 'provider:delete' privilege."""
#     try:
#         await notification_utils.delete_notification(request, provider_id)
#     except notification_utils.NotificationNotFoundError as e:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))



