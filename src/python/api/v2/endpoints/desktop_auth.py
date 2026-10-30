# ==============================================================================
# File: src/python/api/v2/endpoints/desktop_auth.py
# Purpose: Desktop app (CUE GUI) sign-in through the existing Keycloak client,
#          with PKCE (S256) and a loopback redirect (plan 11 B2, design doc 10 section 3).
#          Disabled (404) unless DESKTOP_REDIRECT_URIS is set.
#          Never logs codes, verifiers, state, or tokens.
# ==============================================================================
import os
from typing import Set

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from core.security import OIDCValidator
from v2.type_util.auth import (
    DesktopLoginUrlRequest, DesktopLoginUrlResponse, DesktopLogoutRequest,
    DesktopTokenRequest, TokenResponse,
)
from v2.utils.auth import KeycloakClient, get_keycloak_client

logger = structlog.get_logger(__name__)

SIGN_IN_FAILED = "Sign-in could not be completed. Please try again."


def desktop_redirect_uris() -> Set[str]:
    """Exact allow-list from DESKTOP_REDIRECT_URIS (comma-separated). Empty = feature disabled."""
    raw = os.getenv("DESKTOP_REDIRECT_URIS", "")
    return {u.strip() for u in raw.split(",") if u.strip()}


def require_desktop_enabled() -> None:
    if not desktop_redirect_uris():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


def _check_redirect(redirect_uri: str) -> None:
    if redirect_uri not in desktop_redirect_uris():
        logger.warning("desktop_auth.redirect_rejected")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="redirect_uri is not allowed.")


router = APIRouter(
    prefix="/auth/desktop",
    tags=["V2 - Desktop app sign-in"],
    dependencies=[Depends(require_desktop_enabled)],
)


@router.post("/login-url", response_model=DesktopLoginUrlResponse)
def desktop_login_url(body: DesktopLoginUrlRequest, keycloak_client: KeycloakClient = Depends(get_keycloak_client)):
    """Builds the Keycloak login URL for the desktop app (the app opens it in the system browser)."""
    _check_redirect(body.redirect_uri)
    login_url = keycloak_client.get_desktop_login_url(body.redirect_uri, body.code_challenge, body.state)
    logger.info("desktop_auth.login_url.issued", redirect_uri=body.redirect_uri)
    return DesktopLoginUrlResponse(login_url=login_url)


@router.post("/token", response_model=TokenResponse)
async def desktop_token(
    request: Request, body: DesktopTokenRequest, keycloak_client: KeycloakClient = Depends(get_keycloak_client)
):
    """Exchanges the authorization code + PKCE verifier for tokens (the client secret stays here)."""
    _check_redirect(body.redirect_uri)
    try:
        token_data = await keycloak_client.exchange_code_with_pkce(body.code, body.redirect_uri, body.code_verifier)
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        logger.warning("desktop_auth.token.failed", reason="keycloak_rejected", status_code=code)
        if code in (400, 401):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=SIGN_IN_FAILED)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=SIGN_IN_FAILED)
    except httpx.RequestError:
        logger.warning("desktop_auth.token.failed", reason="network_error")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=SIGN_IN_FAILED)

    # Log who signed in. Best effort: the token comes straight from Keycloak over TLS.
    sub = None
    try:
        sub = OIDCValidator().validate_token(request, token_data.get("access_token", "")).get("sub")
    except HTTPException:
        logger.warning("desktop_auth.token.unverified_sub")
    logger.info("desktop_auth.token.exchanged", sub=sub)
    return TokenResponse(**token_data)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def desktop_logout(body: DesktopLogoutRequest, keycloak_client: KeycloakClient = Depends(get_keycloak_client)):
    """Revokes the desktop refresh token. Always 204 (idempotent); Keycloak errors are only logged."""
    try:
        await keycloak_client.revoke_refresh_token(body.refresh_token)
        logger.info("desktop_auth.logout.revoked")
    except httpx.HTTPStatusError as e:
        logger.warning("desktop_auth.logout.failed", reason="keycloak_rejected", status_code=e.response.status_code)
    except httpx.RequestError:
        logger.warning("desktop_auth.logout.failed", reason="network_error")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
