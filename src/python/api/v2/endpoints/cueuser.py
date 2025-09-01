# File: src/python/api/v2/endpoints/cueuser.py (Updated)

from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from typing import List, Optional

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser as User
from v2.utils import cueuser as cueuser_utils
# --- REMOVED: KeycloakClient dependency ---
from v2.type_util.cueuser import UserResponse, UserCreateRequest, UserUpdateRequest, UserFindResponse, UserRoleUpdateRequest

router = APIRouter(prefix="/cueusers", tags=["V2 - CUE Users"])

@router.get("/me", response_model=UserResponse)
async def get_my_profile(user: User = Depends(get_current_user)):
    """Returns the complete profile for the currently authenticated user."""
    try:
        full_profile = await cueuser_utils.get_user_profile(user.id)
        return UserResponse.model_validate(full_profile)
    except cueuser_utils.UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found in database.")

@router.get("/", response_model=List[UserResponse], dependencies=[Depends(require_privilege("user:read"))])
async def list_users_endpoint():
    """Retrieves a list of all users in the system."""
    try:
        users = await cueuser_utils.list_users()
        return [UserResponse.model_validate(u) for u in users]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- CHANGE: Updated to create a local user profile for an existing Keycloak user ---
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_privilege("user:create"))])
async def create_user_endpoint(
    request: UserCreateRequest,
):
    """
    Allows an admin to create a local CUE user profile for an identity
    that already exists in Keycloak. Requires 'user:create' privilege.
    """
    try:
        new_user = await cueuser_utils.create_new_user(
            user_id=request.user_id,
            email=request.email,
            name=request.name,
            cueusername=request.cueusername,
            role_id=request.role_id,
            ngroup_ids=request.ngroup_ids,
            edpub_id=request.edpub_id
        )
        return UserResponse.model_validate(new_user)
    except ValueError as e:
        # Handle case where user already exists in our DB
        if "already exists" in str(e):
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        # Handle other validation errors (e.g., no ngroup provided)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/find", response_model=List[UserFindResponse], dependencies=[Depends(require_privilege("user:read"))])
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

@router.get("/by_role/{role_id}", response_model=List[UserResponse], dependencies=[Depends(require_privilege("user:read"))])
async def get_users_by_role_endpoint(role_id: UUID):
    """Lists all users assigned to a specific role."""
    users = await cueuser_utils.get_users_by_role(role_id)
    return [UserResponse.model_validate(u) for u in users]

@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_privilege("user:read"))])
async def get_user_by_id_endpoint(user_id: UUID):
    """Retrieves a specific user's profile by their ID."""
    try:
        user_profile = await cueuser_utils.get_user_profile(user_id)
        return UserResponse.model_validate(user_profile)
    except cueuser_utils.UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

@router.get("/by_username/{cueusername}", response_model=UserResponse, dependencies=[Depends(require_privilege("user:read"))])
async def get_user_by_username_endpoint(cueusername: str):
    """Retrieves a specific user's profile by their username."""
    try:
        user_profile = await cueuser_utils.get_user_profile_by_username(cueusername)
        return UserResponse.model_validate(user_profile)
    except cueuser_utils.UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_privilege("user:update"))])
async def update_user_endpoint(user_id: UUID, update_request: UserUpdateRequest):
    """Updates a user's core information."""
    try:
        updated_user = await cueuser_utils.update_user_details(user_id, update_request)
        return UserResponse.model_validate(updated_user)
    except cueuser_utils.UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.patch("/{user_id}/role", response_model=UserResponse, dependencies=[Depends(require_privilege("user:assign_role"))])
async def update_user_role_endpoint(
    user_id: UUID, 
    request: UserRoleUpdateRequest, 
    current_user: User = Depends(get_current_user)
):
    """Assigns a new role to a user."""
    try:
        updated_user = await cueuser_utils.update_user_role(user_id, request.role_id, current_user)
        return UserResponse.model_validate(updated_user)
    except cueuser_utils.UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_privilege("user:delete"))])
async def delete_user_endpoint(user_id: UUID):
    """Deletes a user from the local CUE database. Requires 'user:delete' privilege."""
    try:
        await cueuser_utils.delete_user_fully(user_id)
    except cueuser_utils.UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        # This will catch the user-friendly error from the database layer
        # and send it to the frontend as a 400 Bad Request.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Catch-all for any other unexpected errors.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
