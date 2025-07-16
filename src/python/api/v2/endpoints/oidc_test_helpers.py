# ==============================================================================
# File: src/python/api/v2/endpoints/oidc_test_helpers.py (New)
# Purpose: Provides endpoints to facilitate local OIDC testing.
# This should NOT be deployed to production environments.
# ==============================================================================
import os
import httpx
from fastapi import APIRouter, Body, HTTPException, status
from urllib.parse import urlencode

router = APIRouter(prefix="/oidc-helpers", tags=["V2 - OIDC Test Helpers"])



# --- Configuration ---
CLIENT_ID = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "cue-uat")
CLIENT_SECRET = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET") # Should be set in your .env for local testing
KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER", "https://idfs.sit.earthdatacloud.nasa.gov/realms/cue")
AUTH_ENDPOINT = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/auth"
TOKEN_ENDPOINT = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/token"

REDIRECT_URI = "http://localhost:8080/callback.html"

@router.get("/config")
def get_oidc_test_config():
    """Provides the necessary details for the test frontend to construct login URLs."""
    state = os.urandom(16).hex()
    
    auth_params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": REDIRECT_URI, # This now correctly points to your frontend
        "state": state,
    }
    login_url = f"{AUTH_ENDPOINT}?{urlencode(auth_params)}"
    
    return {
        "login_url": login_url,
        "state": state,
        "redirect_uri": REDIRECT_URI
    }

@router.post("/exchange-code")
async def exchange_code_for_token(request_body: dict = Body(...)):
    """
    Exchanges an authorization code for an access token.
    This is called by your frontend's callback page.
    """
    code = request_body.get("code")
    redirect_uri = request_body.get("redirect_uri")

    if not all([code, redirect_uri, CLIENT_SECRET]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing code, redirect_uri, or client secret configuration.")

    token_payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri, # The URI must match what was used in the initial auth request
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    async with httpx.AsyncClient() as client:
        try:
            token_response = await client.post(TOKEN_ENDPOINT, data=token_payload)
            token_response.raise_for_status()
            return token_response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Failed to exchange code: {e.response.text}")

