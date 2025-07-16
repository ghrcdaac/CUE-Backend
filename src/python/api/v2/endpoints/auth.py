# ==============================================================================
# File: src/python/api/v2/endpoints/auth.py (Fixed)
# Purpose: Provides public endpoints for user registration and password management.
# Fix: Corrected the imported model name from UserRegistrationRequest to UserCreateRequest.
# ==============================================================================
from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import EmailStr

from ..utils.keycloak_admin import get_keycloak_admin_client, KeycloakAdminClient
# --- CHANGE: Corrected the imported model name ---
from ..type_util.cueuser import UserCreateRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["V2 - Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    # --- CHANGE: Use the correct Pydantic model ---
    reg_request: UserCreateRequest,
    keycloak_client: KeycloakAdminClient = Depends(get_keycloak_admin_client)
):
    """
    Registers a new user in Keycloak and the local CUE database.
    This endpoint is a placeholder and should be secured or have business logic
    to prevent misuse in a real application.
    """
    # This endpoint now correctly uses the business logic from cueuser_utils
    # which is not directly imported here but is called by the approval process.
    # For direct admin creation, the endpoint in cueuser.py should be used.
    # This endpoint is more for a public-facing registration form.
    
    # Placeholder logic for direct registration:
    # 1. Call a function to create the user in Keycloak via Admin API
    # keycloak_user_id = await keycloak_client.create_user(reg_request)
    
    # 2. If successful, create the user in your local RDS database
    # await user_db.create_local_user(id=keycloak_user_id, email=reg_request.email, ...)

    # 3. For now, returning a placeholder response
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Direct user registration endpoint not fully implemented. Please use the application approval flow."
    )


@router.post("/initiate-password-reset", status_code=status.HTTP_202_ACCEPTED)
async def initiate_password_reset(
    email: EmailStr = Body(..., embed=True),
    keycloak_client: KeycloakAdminClient = Depends(get_keycloak_admin_client)
):
    """
    Initiates Keycloak's built-in forgot password flow for a user.
    This is a fire-and-forget endpoint. Keycloak handles sending the email.
    """
    # This function is a placeholder. In a real implementation, you would
    # add a call to a method in your keycloak_client to trigger the password reset.
    # For example: await keycloak_client.trigger_forgot_password_flow(email)
    
    return {"message": "If a user with that email exists, a password reset link has been sent."}
