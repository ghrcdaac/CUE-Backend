# ==============================================================================
# File: src/python/api/v2/endpoints/user_application.py (Final)
# Purpose: Provides the REST API endpoints for the user application process.
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from typing import List, Optional

from core.security import get_current_user, require_privilege, get_authenticated_user_claims
from v2.type_util.auth import AuthUser as User, AuthenticatedUserClaims
from v2.utils import user_application as app_utils
from v2.utils.auth import get_keycloak_client, KeycloakClient
from v2.type_util.user_application import (
    UserApplicationCreate, UserApplicationResponse, ApplicationStatus
)
from v2.type_util.cueuser import UserResponse as CueUserResponse

router = APIRouter(prefix="/user_application", tags=["V2 - User Applications"])

@router.post("/", response_model=UserApplicationResponse, status_code=status.HTTP_201_CREATED)
async def submit_user_application(
    application_data: UserApplicationCreate,
    claims: AuthenticatedUserClaims = Depends(get_authenticated_user_claims)
):
    """
    An authenticated user submits an application for an account. This endpoint
    is protected to ensure we have the user's verified Keycloak ID.
    """
    try:
        new_app = await app_utils.submit_application(application_data, claims.id)
        return UserApplicationResponse.model_validate(new_app)
    except ValueError as e:
        # ---  Catch the specific error for duplicate applications ---
        # This is triggered by the UNIQUE index on (user_id, status) WHERE status = 'pending'
        if "already exists" in str(e):
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A pending application for this user already exists.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=List[UserApplicationResponse], dependencies=[Depends(require_privilege("approve_user"))])
async def list_all_applications(
    user: User = Depends(get_current_user),
    status: Optional[ApplicationStatus] = Query(None, description="Filter applications by status.")
):
    """
    Lists user applications. Admins see all, others see applications
    for their own ngroup. Requires 'approve_user' privilege.
    """
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
    role_id: UUID = Query(..., description="The ID of the role to assign to the new user.")
    # --- CHANGE: Removed the KeycloakClient dependency ---
):
    """
    Approves a user application, creating the user in the local CUE database.
    """
    try:
        created_user = await app_utils.approve_application(application_id, role_id)
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
