# ==============================================================================
# File: src/python/api/v2/endpoints/cueuser.py (Final)
# Purpose: Provides the v2 REST API endpoints for all user management.
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from typing import List, Optional

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser as User
from v2.utils import cueuser as cueuser_utils
from v2.utils.auth import get_keycloak_client, KeycloakClient
from v2.type_util.cueuser import UserResponse, UserCreateRequest, UserUpdateRequest, UserFindResponse

router = APIRouter(prefix="/cueusers", tags=["V2 - CUE Users"])

@router.get("/me", response_model=UserResponse)
async def get_my_profile(user: User = Depends(get_current_user)):
    """Returns the complete profile for the currently authenticated user."""
    try:
        full_profile = await cueuser_utils.get_user_profile(user.id)
        return UserResponse.model_validate(full_profile)
    except cueuser_utils.UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found in database.")

@router.get("/", response_model=List[UserResponse], dependencies=[Depends(require_privilege("admin"))])
async def list_users_endpoint():
    """
    Retrieves a list of all users in the system.
    Requires 'admin' privilege.
    """
    try:
        users = await cueuser_utils.list_users()
        return [UserResponse.model_validate(u) for u in users]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_privilege("create_user"))])
async def create_user_endpoint(
    request: UserCreateRequest,
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
):
    """
    Allows an admin to create a new user directly in Keycloak and the local DB.
    Requires 'create_user' privilege.
    """
    try:
        new_user = await cueuser_utils.create_new_user(
            email=request.email, name=request.name, cueusername=request.cueusername,
            role_id=request.role_id, ngroup_ids=request.ngroup_ids, edpub_id=request.edpub_id,
            keycloak_client=keycloak_client
        )
        return UserResponse(**new_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/find", response_model=List[UserFindResponse], dependencies=[Depends(require_privilege("view_provider"))])
async def find_user_endpoint(
    email: Optional[str] = Query(None, description="Email to search for (case-insensitive, partial match)."),
    cueusername: Optional[str] = Query(None, description="Username to search for (case-insensitive, partial match)."),
    name: Optional[str] = Query(None, description="Name to search for (case-insensitive, partial match)."),
    edpub_id: Optional[str] = Query(None, description="Exact EdPub ID to search for.")
):
    """Finds users based on various criteria."""
    try:
        users = await cueuser_utils.find_users_by_criteria(email, cueusername, name, edpub_id)
        return [UserFindResponse.model_validate(u) for u in users]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/by_role/{role_id}", response_model=List[UserResponse], dependencies=[Depends(require_privilege("admin"))])
async def get_users_by_role_endpoint(role_id: UUID):
    """Lists all users assigned to a specific role."""
    users = await cueuser_utils.get_users_by_role(role_id)
    return [UserResponse.model_validate(u) for u in users]

@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_privilege("view_provider"))])
async def get_user_by_id_endpoint(user_id: UUID):
    """Retrieves a specific user's profile by their ID."""
    try:
        user_profile = await cueuser_utils.get_user_profile(user_id)
        return UserResponse(**user_profile)
    except cueuser_utils.UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

@router.get("/by_username/{cueusername}", response_model=UserResponse, dependencies=[Depends(require_privilege("view_provider"))])
async def get_user_by_username_endpoint(cueusername: str):
    """Retrieves a specific user's profile by their username."""
    try:
        user_profile = await cueuser_utils.get_user_profile_by_username(cueusername)
        return UserResponse(**user_profile)
    except cueuser_utils.UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_privilege("admin"))])
async def update_user_endpoint(user_id: UUID, update_request: UserUpdateRequest):
    """Updates a user's core information."""
    try:
        updated_user = await cueuser_utils.update_user_details(user_id, update_request)
        return UserResponse(**updated_user)
    except cueuser_utils.UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_privilege("admin"))])
async def delete_user_endpoint(user_id: UUID):
    """
    Deletes a user from the local CUE database. Requires 'admin' privilege.
    This operation does NOT delete the user from Keycloak.
    """
    try:
        # --- The KeycloakClient dependency is no longer needed here ---
        await cueuser_utils.delete_user_fully(user_id)
    except cueuser_utils.UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
