# ==============================================================================
# File: src/python/api/v2/endpoints/auth.py (New & Consolidated)
# Purpose: Provides all necessary OIDC authentication and user management endpoints.
# ==============================================================================
from fastapi import APIRouter, Body, Depends, HTTPException, status, Request
from urllib.parse import urlencode
import httpx
import os
from typing import Dict, Any

from core.security import get_current_user, User
from v2.utils.auth import get_keycloak_client, KeycloakClient, get_user_login_status
from v2.type_util.auth import (
    TokenIntrospectionRequest, TokenIntrospectionResponse, 
    LogoutUrlRequest, LogoutUrlResponse, UserStatusResponse
)

router = APIRouter(prefix="/auth", tags=["V2 - Authentication"])

@router.post("/initiate-password-reset", status_code=status.HTTP_202_ACCEPTED)
async def initiate_password_reset(
    user: User = Depends(get_current_user), # Requires user to be logged in
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
):
    """
    Initiates Keycloak's 'forgot password' flow for the currently logged-in user.
    """
    try:
        await keycloak_client.initiate_password_reset(str(user.id))
        return {"message": "Password reset process initiated. Please check your email."}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Failed to initiate password reset.")

@router.post("/introspect", response_model=Dict[str, Any])
async def introspect_token(
    request: TokenIntrospectionRequest,
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
):
    """
    Proxies a token introspection request to Keycloak. Useful for debugging.
    This endpoint itself is not protected to allow introspection of any token.
    """
    introspection_endpoint = f"{keycloak_client.base_url}/protocol/openid-connect/token/introspect"
    payload = {
        "token": request.token,
        "client_id": keycloak_client.admin_client_id,
        "client_secret": keycloak_client.admin_client_secret,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(introspection_endpoint, data=payload)
        return response.json()

@router.get("/userinfo", response_model=User)
async def get_user_info(user: User = Depends(get_current_user)):
    """
    Returns the user information object that was parsed and enriched from the
    validated JWT access token. This is a secure way to get user details.
    """
    return user

@router.post("/logout-url", response_model=LogoutUrlResponse)
def get_logout_url(request: LogoutUrlRequest):
    """Constructs the full logout URL for Keycloak."""
    logout_endpoint = f"{os.getenv('KEYCLOAK_ISSUER')}/protocol/openid-connect/logout"
    # The frontend URL must be a "Valid Post Logout Redirect URI" in Keycloak
    post_logout_redirect_uri = os.getenv("FRONTEND_URL", "http://localhost:8080")
    
    params = {
        "id_token_hint": request.id_token_hint,
        "post_logout_redirect_uri": post_logout_redirect_uri
    }
    return LogoutUrlResponse(logout_url=f"{logout_endpoint}?{urlencode(params)}")

@router.get("/status", response_model=UserStatusResponse)
async def get_user_status(user: User = Depends(get_current_user)):
    """
    Checks if the authenticated user is registered, pending approval, or new.
    This is the first endpoint the frontend should call after a user logs in.
    """
    status = await get_user_login_status(user.id)
    return UserStatusResponse(status=status)