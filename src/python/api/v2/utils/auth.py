# ==============================================================================
# File: src/python/api/v2/utils/auth.py
# Purpose: Handles all server-to-server communication with Keycloak and auth logic.
# --- to add detailed timing logs for all external IDFS API calls ---
# ==============================================================================
import os
import time
import httpx
import structlog
from typing import Dict, Any, Optional
from uuid import UUID
from jose import jwt
from urllib.parse import urlencode
from fastapi import Request

from v2.database_util import cueuser as user_db
from v2.database_util import user_application as app_db

logger = structlog.get_logger(__name__)

class KeycloakClient:
    """
    A client for interacting with Keycloak's APIs using a shared httpx client.
    """
    def __init__(self, http_client: httpx.AsyncClient):
        self.http_client = http_client
        self.base_url = os.getenv("KEYCLOAK_ISSUER")
        self.admin_client_id = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID")
        self.admin_client_secret = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET")

        if not all([self.base_url, self.admin_client_id, self.admin_client_secret]):
            raise ValueError("Missing required Keycloak admin environment variables.")

        self.token_url = f"{self.base_url}/protocol/openid-connect/token"
        self.auth_url = f"{self.base_url}/protocol/openid-connect/auth"
        self.admin_api_url = f"{self.base_url.replace('/realms/', '/admin/realms/')}"
        self._access_token: Optional[str] = None
        self._token_expires_at: int = 0

    def get_login_url(self) -> (str, str):
        """Generates the OIDC login URL."""
        state = os.urandom(16).hex()
        redirect_uri = os.getenv("FRONTEND_CALLBACK_URL", "http://localhost:3000/callback")
        params = {
            "client_id": self.admin_client_id,
            "response_type": "code",
            "scope": "openid profile email offline_access",
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"{self.auth_url}?{urlencode(params)}", state

    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchanges an authorization code for a full set of tokens."""
        payload = {
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": redirect_uri, "client_id": self.admin_client_id,
            "client_secret": self.admin_client_secret,
        }
        
        log_ctx = {"idfs_endpoint": self.token_url, "grant_type": "authorization_code"}
        logger.info("idfs.api.call.start", **log_ctx)
        t0 = time.perf_counter()
        
        response = await self.http_client.post(self.token_url, data=payload)
        
        t1 = time.perf_counter()
        duration_ms = round((t1 - t0) * 1000, 2)
        logger.info("idfs.api.call.complete", duration_ms=duration_ms, status_code=response.status_code, **log_ctx)
        
        response.raise_for_status()
        return response.json()

    async def _get_service_token(self) -> str:
        """Gets a service account access token, caching it until expiration."""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.admin_client_id,
            "client_secret": self.admin_client_secret,
        }
        
        log_ctx = {"idfs_endpoint": self.token_url, "grant_type": "client_credentials"}
        logger.info("idfs.api.call.start", **log_ctx)
        t0 = time.perf_counter()
        
        response = await self.http_client.post(self.token_url, data=payload)

        t1 = time.perf_counter()
        duration_ms = round((t1 - t0) * 1000, 2)
        logger.info("idfs.api.call.complete", duration_ms=duration_ms, status_code=response.status_code, **log_ctx)

        response.raise_for_status()
        token_data = response.json()
        self._access_token = token_data["access_token"]
        self._token_expires_at = time.time() + token_data.get("expires_in", 300) - 30
        return self._access_token

    async def create_user(self, email: str, username: str, first_name: str, last_name: str) -> str:
        """Creates a user in Keycloak via the Admin API."""
        token = await self._get_service_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        user_representation = {
            "username": username, "email": email, "firstName": first_name,
            "lastName": last_name, "enabled": True, "emailVerified": True,
        }
        users_url = f"{self.admin_api_url}/users"
        
        log_ctx = {"idfs_endpoint": users_url, "action": "create_user"}
        logger.info("idfs.api.call.start", **log_ctx)
        t0 = time.perf_counter()

        response = await self.http_client.post(users_url, headers=headers, json=user_representation)
        
        t1 = time.perf_counter()
        duration_ms = round((t1 - t0) * 1000, 2)
        logger.info("idfs.api.call.complete", duration_ms=duration_ms, status_code=response.status_code, **log_ctx)

        if response.status_code == 409:
            raise ValueError(f"User with username '{username}' or email '{email}' already exists.")
        response.raise_for_status()
        
        location_url = response.headers.get("Location")
        if not location_url:
            get_resp = await self.http_client.get(f"{users_url}?username={username}", headers=headers)
            get_resp.raise_for_status()
            return get_resp.json()[0]['id']
        return location_url.split("/")[-1]

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Exchanges a refresh token for a new access token."""
        payload = {
            "grant_type": "refresh_token", "refresh_token": refresh_token,
            "client_id": self.admin_client_id, "client_secret": self.admin_client_secret,
        }

        log_ctx = {"idfs_endpoint": self.token_url, "grant_type": "refresh_token"}
        logger.info("idfs.api.call.start", **log_ctx)
        t0 = time.perf_counter()
        
        response = await self.http_client.post(self.token_url, data=payload)
        
        t1 = time.perf_counter()
        duration_ms = round((t1 - t0) * 1000, 2)
        logger.info("idfs.api.call.complete", duration_ms=duration_ms, status_code=response.status_code, **log_ctx)
        
        response.raise_for_status()
        return response.json()

    async def delete_user(self, user_id: UUID):
        """Deletes a user from Keycloak via the Admin API."""
        token = await self._get_service_token()
        headers = {"Authorization": f"Bearer {token}"}
        delete_url = f"{self.admin_api_url}/users/{user_id}"
        
        log_ctx = {"idfs_endpoint": delete_url, "action": "delete_user"}
        logger.info("idfs.api.call.start", **log_ctx)
        t0 = time.perf_counter()
        
        response = await self.http_client.delete(delete_url, headers=headers)

        t1 = time.perf_counter()
        duration_ms = round((t1 - t0) * 1000, 2)
        logger.info("idfs.api.call.complete", duration_ms=duration_ms, status_code=response.status_code, **log_ctx)
        
        if response.status_code not in [204, 404]:
            logger.error("keycloak.admin.delete.failed", user_id=str(user_id), status_code=response.status_code)
    
    async def initiate_password_reset(self, user_id: str):
        """Triggers the 'Update Password' required action for a user."""
        token = await self._get_service_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = ["UPDATE_PASSWORD"]
        reset_url = f"{self.admin_api_url}/users/{user_id}/execute-actions-email"
        params = {"redirect_uri": os.getenv("FRONTEND_URL", "http://localhost:3000")}

        log_ctx = {"idfs_endpoint": reset_url, "action": "initiate_password_reset"}
        logger.info("idfs.api.call.start", **log_ctx)
        t0 = time.perf_counter()
        
        response = await self.http_client.put(reset_url, headers=headers, json=payload, params=params)

        t1 = time.perf_counter()
        duration_ms = round((t1 - t0) * 1000, 2)
        logger.info("idfs.api.call.complete", duration_ms=duration_ms, status_code=response.status_code, **log_ctx)

        response.raise_for_status()

    async def introspect_token(self, token: str) -> Dict[str, Any]:
        """Proxies a token introspection request to Keycloak."""
        introspection_endpoint = f"{self.base_url}/protocol/openid-connect/token/introspect"
        payload = {
            "token": token,
            "client_id": self.admin_client_id,
            "client_secret": self.admin_client_secret,
        }

        log_ctx = {"idfs_endpoint": introspection_endpoint, "action": "introspect_token"}
        logger.info("idfs.api.call.start", **log_ctx)
        t0 = time.perf_counter()
        
        response = await self.http_client.post(introspection_endpoint, data=payload)
        
        t1 = time.perf_counter()
        duration_ms = round((t1 - t0) * 1000, 2)
        logger.info("idfs.api.call.complete", duration_ms=duration_ms, status_code=response.status_code, **log_ctx)
        
        response.raise_for_status()
        return response.json()

def get_keycloak_client(request: Request) -> KeycloakClient:
    """Dependency to provide a KeycloakClient with the shared httpx client."""
    return KeycloakClient(http_client=request.app.state.http_client)

async def get_user_login_status(request: Request, user_id: UUID) -> str:
    """Checks the database to determine a user's status for the login workflow."""
    logger.info("auth.status.checking", user_id=str(user_id))
    async with request.state.pool.acquire() as conn:
        if await user_db.user_exists_by_id(conn, user_id):
            return "registered"
        if await app_db.get_pending_application_by_user_id(conn, user_id):
            return "pending_approval"
        return "unregistered"

