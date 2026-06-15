# ==============================================================================
# File: src/python/api/v2/endpoints/user_application.py (Corrected)
# --- MODIFIED to pass the request object to the utility layer ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Header
from uuid import UUID
from typing import List, Optional

from core.security import get_current_user, require_privilege, get_authenticated_user_claims
from v2.type_util.auth import AuthUser as User, AuthenticatedUserClaims
from v2.utils import user_application as app_utils
from v2.type_util.user_application import (
    UserApplicationCreate, UserApplicationResponse, ApplicationStatus
)
from v2.type_util.cueuser import UserResponse as CueUserResponse

router = APIRouter(prefix="/user_application", tags=["V2 - User Applications"])

@router.post("/", response_model=UserApplicationResponse, status_code=status.HTTP_201_CREATED)
async def submit_user_application(
    request: Request,
    application_data: UserApplicationCreate,
    claims: AuthenticatedUserClaims = Depends(get_authenticated_user_claims)
):
    """
    An authenticated user submits an application for an account. This endpoint
    is protected to ensure we have the user's verified Keycloak ID.
    """
    try:
        new_app = await app_utils.submit_application(request, application_data, claims.id)
        return UserApplicationResponse.model_validate(new_app)
    except ValueError as e:
        if "spam" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This email address has been marked as spam and is not permitted to submit applications.")
        if "already exists" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A pending application for this user already exists.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=List[UserApplicationResponse], dependencies=[Depends(require_privilege("application:read"))])
async def list_all_applications(
    request: Request,
    user: User = Depends(get_current_user),
    # Read the active ngroup ID directly from the header
    active_ngroup_id: Optional[str] = Header(None, alias="x-active-ngroup-id"),
    status: Optional[ApplicationStatus] = Query(None, description="Filter applications by status.")
):
    """
    Lists user applications, filtered by the selected ngroup. Admins see all,
    others see applications for their own ngroups. Requires 'application:read' privilege.
    """
    try:
        # Pass the header value and user object to the utility function
        apps = await app_utils.list_applications(request, user, active_ngroup_id, status)
        return [UserApplicationResponse.model_validate(app) for app in apps]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{application_id}", response_model=UserApplicationResponse, dependencies=[Depends(require_privilege("application:read"))])
async def get_single_application(request: Request, application_id: UUID):
    """Retrieves a single user application by its ID."""
    try:
        app = await app_utils.get_application(request, application_id)
        return UserApplicationResponse.model_validate(app)
    except app_utils.ApplicationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

@router.post("/{application_id}/approve", response_model=CueUserResponse, dependencies=[Depends(require_privilege("application:approve"))])
async def approve_application_endpoint(
    request: Request,
    application_id: UUID,
    approver: User = Depends(get_current_user),
    role_id: UUID = Query(..., description="The ID of the role to assign to the new user.")
):
    """
    Approves a user application, creating the user in the local CUE database.
    """
    try:
        created_user = await app_utils.approve_application(
            request=request,
            application_id=application_id,
            role_id_to_assign=role_id,
            approver=approver
        )
        return CueUserResponse.model_validate(created_user)
    except (app_utils.ApplicationNotFoundError, app_utils.ApplicationInvalidStateError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        # This will catch permission errors from the business logic layer
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{application_id}/reject", response_model=UserApplicationResponse, dependencies=[Depends(require_privilege("application:approve"))])
async def reject_application_endpoint(
    request: Request,
    application_id: UUID,
    mark_as_spam: bool = Query(False, description="Mark the applicant email as spam and block future applications from it.")
):
    """Rejects a pending user application."""
    try:
        rejected_app = await app_utils.reject_application(request, application_id, mark_as_spam=mark_as_spam)
        return UserApplicationResponse.model_validate(rejected_app)
    except (app_utils.ApplicationNotFoundError, app_utils.ApplicationInvalidStateError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

