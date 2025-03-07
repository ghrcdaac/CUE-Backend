from asyncio.log import logger
from fastapi import APIRouter, HTTPException, Query, Depends, Request, status
from uuid import UUID
from typing import List, Optional

from utils.user_application import (create_user_application, get_user_application,
                                      update_user_application, delete_user_application,
                                      list_user_applications, UserApplicationNotFoundError, get_ngroups_for_form,
                                         get_providers_for_ngroup)
from lambda_utils.type_util.user_application import (UserApplicationCreate,
                                                     UserApplicationReturn,
                                                     UserApplicationUpdate)

from lambda_utils.type_util.ngroup import NgroupListReturn
from lambda_utils.type_util.provider import ProviderListReturn

router = APIRouter(prefix="/user_application", tags=["user_application"])

@router.post("/", response_model=UserApplicationReturn)
async def create_user_application_endpoint(user_application: UserApplicationCreate):
    try:
        return await create_user_application(user_application)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/ngroups", response_model=List[NgroupListReturn])
async def get_ngroups_for_form_endpoint():
    try:
        return await get_ngroups_for_form()
    except Exception as e:
        logger.error(f"Error getting ngroups for form: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve ngroups for form")

@router.get("/ngroups/{ngroup_id}/providers", response_model=List[ProviderListReturn])
async def get_providers_for_ngroup_endpoint(ngroup_id: UUID):
    try:
        return await get_providers_for_ngroup(ngroup_id)
    except Exception as e:
        logger.error(f"Error getting providers for ngroup: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve providers for ngroup")


@router.get("/{user_application_id}", response_model=UserApplicationReturn)
async def get_user_application_endpoint(user_application_id: UUID):
    try:
        user_application = await get_user_application(user_application_id)
        return user_application
    except UserApplicationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e

@router.patch("/{user_application_id}", response_model=UserApplicationReturn)
async def update_user_application_endpoint(user_application_id: UUID, user_application_update: UserApplicationUpdate):
    try:
        updated_user_application = await update_user_application(user_application_id, user_application_update)
        return updated_user_application
    except UserApplicationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e

@router.delete("/{user_application_id}", response_model=bool)
async def delete_user_application_endpoint(user_application_id: UUID):
    try:
        success = await delete_user_application(user_application_id)
        return success
    except UserApplicationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e





@router.get("/", response_model=List[UserApplicationReturn])
async def list_user_applications_endpoint():
    try:
        return await list_user_applications()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e