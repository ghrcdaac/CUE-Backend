from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from typing import List, Optional

from utils.user_application import (create_user_application, get_user_application,
                                      update_user_application, delete_user_application,
                                      list_user_applications, UserApplicationNotFoundError)
from lambda_utils.type_util.user_application import (UserApplicationCreate,
                                                     UserApplicationReturn,
                                                     UserApplicationUpdate)

router = APIRouter(prefix="/user_application", tags=["user_application"])

@router.post("/", response_model=UserApplicationReturn)
async def create_user_application_endpoint(user_application: UserApplicationCreate):
    try:
        return await create_user_application(user_application)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{user_application_id}", response_model=UserApplicationReturn)
async def get_user_application_endpoint(user_application_id: UUID):
    try:
        user_application = await get_user_application(user_application_id)
        return user_application
    except UserApplicationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{user_application_id}", response_model=UserApplicationReturn)
async def update_user_application_endpoint(user_application_id: UUID, user_application_update: UserApplicationUpdate):
    try:
        updated_user_application = await update_user_application(user_application_id, user_application_update)
        return updated_user_application
    except UserApplicationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{user_application_id}", response_model=bool)
async def delete_user_application_endpoint(user_application_id: UUID):
    try:
        success = await delete_user_application(user_application_id)
        return success
    except UserApplicationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[UserApplicationReturn])
async def list_user_applications_endpoint():
    try:
        return await list_user_applications()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))