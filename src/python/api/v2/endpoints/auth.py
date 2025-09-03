# ==============================================================================
# File: src/python/api/v2/endpoints/auth.py
# Purpose: Provides all necessary OIDC authentication and user management endpoints.
# --- MODIFIED to pass the request object down to the utility layer ---
# ==============================================================================
from fastapi import APIRouter, Body, Depends, HTTPException, status, Request, Response
from urllib.parse import urlencode
import httpx
import os
from typing import Dict, Any

from core.security import get_current_user, get_authenticated_user_claims
from v2.type_util.auth import (
    AuthUser, AuthenticatedUserClaims, LogoutUrlRequest, LogoutUrlResponse, 
    UserStatusResponse, AccessTokenResponse, LoginUrlResponse, 
    CodeExchangeRequest, TokenResponse, TokenIntrospectionRequest, UserClaimsResponse,
    RefreshTokenRequest
)
from v2.utils.auth import get_keycloak_client, KeycloakClient, get_user_login_status

router = APIRouter(prefix="/auth", tags=["V2 - Authentication"])
timeout = httpx.Timeout(30.0, connect=30.0)
# --- Initial Login Flow ---

@router.get("/login-url", response_model=LoginUrlResponse)
def get_login_url(keycloak_client: KeycloakClient = Depends(get_keycloak_client)):
    """
    Provides the frontend with a secure URL to redirect the user to for login.
    """
    login_url, state = keycloak_client.get_login_url()
    return LoginUrlResponse(login_url=login_url, state=state)

@router.post("/exchange-code", response_model=TokenResponse)
async def exchange_code(
    request: CodeExchangeRequest,
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
):
    """
    Handles the callback from Keycloak. Exchanges the authorization code for tokens
    and returns them directly in the response body.
    """
    try:
        token_data = await keycloak_client.exchange_code_for_tokens(request.code, request.redirect_uri)
        return TokenResponse(**token_data)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to exchange code: {e.response.text}")

# --- User Status and Token Management ---

# --- MODIFIED: This endpoint now accepts the request object and passes it down ---
@router.get("/status", response_model=UserStatusResponse)
async def get_user_status(
    request: Request, # <-- Added the request object
    claims: AuthenticatedUserClaims = Depends(get_authenticated_user_claims)
):
    """
    Checks if the authenticated user is registered, pending approval, or new.
    This is the first endpoint the frontend should call after a user logs in.
    """
    # Pass the request object to the utility function
    status = await get_user_login_status(request, claims.id)
    return UserStatusResponse(status=status)

@router.get("/claims", response_model=UserClaimsResponse)
async def get_user_claims_for_registration(
    claims: AuthenticatedUserClaims = Depends(get_authenticated_user_claims)
):
    """
    For a user who has authenticated but is not yet registered in CUE,
    this endpoint returns their basic claims from the token to pre-fill
    the application form.
    """
    return UserClaimsResponse(
        name=claims.name,
        email=claims.email,
        cueusername=claims.cueusername
    )

@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
):
    """Uses a refresh token from the request body to get a new access token."""
    try:
        new_tokens = await keycloak_client.refresh_access_token(request.refresh_token)
        return AccessTokenResponse(**new_tokens)
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")

@router.get("/userinfo", response_model=AuthUser)
async def get_user_info(user: AuthUser = Depends(get_current_user)):
    """Returns the user object parsed and enriched from the validated JWT."""
    return user

@router.post("/logout-url", response_model=LogoutUrlResponse)
def get_logout_url(request: LogoutUrlRequest):
    """Constructs the full logout URL for Keycloak."""
    logout_endpoint = f"{os.getenv('KEYCLOAK_ISSUER')}/protocol/openid-connect/logout"
    post_logout_redirect_uri = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    params = {"id_token_hint": request.id_token_hint, "post_logout_redirect_uri": post_logout_redirect_uri}
    return LogoutUrlResponse(logout_url=f"{logout_endpoint}?{urlencode(params)}")

@router.post("/initiate-password-reset", status_code=status.HTTP_202_ACCEPTED)
async def initiate_password_reset(
    user: AuthUser = Depends(get_current_user),
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
    """
    introspection_endpoint = f"{keycloak_client.base_url}/protocol/openid-connect/token/introspect"
    payload = {
        "token": request.token,
        "client_id": keycloak_client.admin_client_id,
        "client_secret": keycloak_client.admin_client_secret,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(introspection_endpoint, data=payload)
        return response.json()

