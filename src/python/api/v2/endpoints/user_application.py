# ==============================================================================
# File: src/python/api/v2/endpoints/user_applications.py (New)
# Purpose: Provides the REST API endpoints for the user application process.
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from typing import List, Optional

from core.security import get_current_user, require_privilege, User
from ..utils import user_application as app_utils
from ..utils.keycloak_admin import get_keycloak_admin_client, KeycloakAdminClient
from ..type_util.user_application import (
    UserApplicationCreate, UserApplicationResponse, ApplicationStatus
)
from ..type_util.cueuser import UserResponse as CueUserResponse # To return the created user

router = APIRouter(prefix="/applications", tags=["V2 - User Applications"])

@router.post("/", response_model=UserApplicationResponse, status_code=status.HTTP_201_CREATED)
async def submit_user_application(application_data: UserApplicationCreate):
    """
    Public endpoint for a new user to submit an application for an account.
    """
    try:
        new_app = await app_utils.submit_application(application_data)
        return UserApplicationResponse.model_validate(new_app)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[UserApplicationResponse], dependencies=[Depends(require_privilege("approve_user"))])
async def list_all_applications(
    user: User = Depends(get_current_user),
    status: Optional[ApplicationStatus] = Query(None, description="Filter applications by status.")
):
    """
    Lists user applications. Admins/Managers see all, others see applications
    for their own ngroup. Requires 'approve_user' privilege.
    """
    # If user is not an admin, they can only see applications for their active ngroup
    ngroup_filter = None
    if "admin" not in user.roles:
        if not user.active_ngroup_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Active-Ngroup-Id header is required for non-admins.")
        ngroup_filter = UUID(user.active_ngroup_id)

    apps = await app_utils.list_applications(ngroup_id=ngroup_filter, status=status)
    return [UserApplicationResponse.model_validate(app) for app in apps]

@router.get("/{application_id}", response_model=UserApplicationResponse, dependencies=[Depends(require_privilege("approve_user"))])
async def get_single_application(application_id: UUID):
    """Retrieves a single user application by its ID."""
    try:
        app = await app_utils.get_application(application_id)
        return UserApplicationResponse.model_validate(app)
    except app_utils.ApplicationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

@router.post("/{application_id}/approve", response_model=CueUserResponse, dependencies=[Depends(require_privilege("approve_user"))])
async def approve_application_endpoint(
    application_id: UUID,
    role_id: UUID = Query(..., description="The ID of the role to assign to the new user."),
    keycloak_client: KeycloakAdminClient = Depends(get_keycloak_admin_client)
):
    """
    Approves a user application, creating the user in Keycloak and the local DB.
    """
    try:
        created_user = await app_utils.approve_application(application_id, role_id, keycloak_client)
        return CueUserResponse.model_validate(created_user)
    except (app_utils.ApplicationNotFoundError, app_utils.ApplicationInvalidStateError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{application_id}/reject", response_model=UserApplicationResponse, dependencies=[Depends(require_privilege("approve_user"))])
async def reject_application_endpoint(application_id: UUID):
    """Rejects a pending user application."""
    try:
        rejected_app = await app_utils.reject_application(application_id)
        return UserApplicationResponse.model_validate(rejected_app)
    except (app_utils.ApplicationNotFoundError, app_utils.ApplicationInvalidStateError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
