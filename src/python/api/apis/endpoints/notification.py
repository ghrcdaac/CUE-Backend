from fastapi import APIRouter, HTTPException, Depends, Body
from uuid import UUID
from typing import List
from lambda_utils.type_util.notification import (NotificationReturn, Notification)
from utils.notification import create_notifications,NotificationNotFoundError, get_notification, get_notification_by_user_id,update_notification

# Authentication Imports
from utils.auth import get_cognito_auth

router = APIRouter(prefix="/notification", tags=["notification"])

@router.get("/user", response_model=List[NotificationReturn])
async def lookup_notification_by_user(
    current_user: dict = Depends(get_cognito_auth().get_current_user)
):
    """Finds a notification based on user_id (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_id = current_user['id']
        notification = await get_notification_by_user_id(user_id) # Pass user_id
        return notification
    except NotificationNotFoundError:
        raise HTTPException(status_code=404, detail=f"notification not found for user_id: {user_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{notification_id}", response_model=NotificationReturn)
async def update_notification(
    notification_id: UUID,
    data: Notification = Body(...),
    current_user: dict = Depends(get_cognito_auth().get_current_user)
):
    """Updates a notification (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        updated_notification = await update_notification(notification_id, data)
        return updated_notification
    except NotificationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/{notification_id}", response_model=NotificationReturn)
async def get_notification_by_id(
    notification_id: UUID,
    current_user: dict = Depends(get_cognito_auth().get_current_user)
):
    """Retrieves a notification by ID, filtered by ngroup_id (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        notification = await get_notification(notification_id)
        return notification
    except NotificationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.post("/", response_model=List[NotificationReturn])
async def add_notification_preference(
    notification: List[Notification],
    current_user: dict = Depends(get_cognito_auth().get_current_user)
):
    """Creates a new notification (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_id = current_user['id']
        return await create_notifications(notification, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))