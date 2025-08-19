# ==============================================================================
# File: src/python/api/v2/utils/auth.py (Final)
# Purpose: Handles all server-to-server communication with Keycloak and auth logic.
# ==============================================================================
import os
import time
import httpx
import structlog
from typing import Dict, Any, Optional
from uuid import UUID
from jose import jwt
from urllib.parse import urlencode

from core.db import get_db_connection
from v2.database_util import cueuser as user_db
from v2.database_util import user_application as app_db

logger = structlog.get_logger(__name__)

class KeycloakClient:
    """
    A client for interacting with Keycloak's OIDC and Admin REST APIs.
    """
    def __init__(self):
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
        """Generates the OIDC login URL and a state parameter for CSRF protection."""
        state = os.urandom(16).hex()
        redirect_uri = os.getenv("FRONTEND_CALLBACK_URL", "http://localhost:3000/callback")
        
        params = {
            "client_id": self.admin_client_id,
            "response_type": "code",
            "scope": "openid profile email offline_access", # Request offline_access to get a refresh token
            "redirect_uri": redirect_uri,
            "state": state,
        }
        login_url = f"{self.auth_url}?{urlencode(params)}"
        return login_url, state

    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchanges an authorization code for a full set of tokens."""
        logger.info("keycloak.token.exchanging_code")
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.admin_client_id,
            "client_secret": self.admin_client_secret,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=payload)
            response.raise_for_status()
            return response.json()

    async def _get_service_token(self) -> str:
        """Gets a service account access token using client_credentials grant."""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        logger.info("keycloak.admin.token.fetching", client_id=self.admin_client_id)
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.admin_client_id,
            "client_secret": self.admin_client_secret,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=payload)
            response.raise_for_status()
            token_data = response.json()
            self._access_token = token_data["access_token"]
            self._token_expires_at = time.time() + token_data.get("expires_in", 300) - 30
            
            try:
                decoded_token = jwt.get_unverified_claims(self._access_token)
                logger.info("keycloak.admin.token.received_and_decoded", claims=decoded_token)
            except Exception as e:
                logger.error("keycloak.admin.token.decode_failed", error=str(e))

            return self._access_token

    async def create_user(self, email: str, username: str, first_name: str, last_name: str) -> str:
        """Creates a user in Keycloak via the Admin API and returns the new user's ID."""
        token = await self._get_service_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        user_representation = {
            "username": username, "email": email, "firstName": first_name,
            "lastName": last_name, "enabled": True, "emailVerified": True,
        }
        users_url = f"{self.admin_api_url}/users"
        
        logger.info("keycloak.admin.api.create_user", target_url=users_url)
        async with httpx.AsyncClient() as client:
            response = await client.post(users_url, headers=headers, json=user_representation)
            if response.status_code == 409:
                raise ValueError(f"User with username '{username}' or email '{email}' already exists.")
            response.raise_for_status()
            
            location_url = response.headers.get("Location")
            if not location_url:
                response_get = await client.get(f"{users_url}?username={username}", headers=headers)
                response_get.raise_for_status()
                return response_get.json()[0]['id']
            return location_url.split("/")[-1]

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Exchanges a refresh token for a new access token."""
        logger.info("keycloak.token.refreshing")
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.admin_client_id,
            "client_secret": self.admin_client_secret,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=payload)
            response.raise_for_status()
            return response.json()

    async def delete_user(self, user_id: UUID):
        """Deletes a user from Keycloak via the Admin API."""
        token = await self._get_service_token()
        headers = {"Authorization": f"Bearer {token}"}
        delete_url = f"{self.admin_api_url}/users/{user_id}"
        async with httpx.AsyncClient() as client:
            response = await client.delete(delete_url, headers=headers)
            if response.status_code not in [204, 404]:
                logger.error("keycloak.admin.delete.failed", user_id=str(user_id), status_code=response.status_code)
    
    async def initiate_password_reset(self, user_id: str):
        """Triggers the 'Update Password' required action for a user."""
        token = await self._get_service_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = ["UPDATE_PASSWORD"]
        reset_url = f"{self.admin_api_url}/users/{user_id}/execute-actions-email"
        
        async with httpx.AsyncClient() as client:
            params = {"redirect_uri": os.getenv("FRONTEND_URL", "http://localhost:3000")}
            response = await client.put(reset_url, headers=headers, json=payload, params=params)
            response.raise_for_status()

# Singleton instance for easy dependency injection
keycloak_client = KeycloakClient()

def get_keycloak_client() -> KeycloakClient:
    return keycloak_client

async def get_user_login_status(user_id: UUID) -> str:
    """
    Checks the database to determine a user's status for the login workflow.
    """
    logger.info("auth.status.checking", user_id=str(user_id))
    async with get_db_connection() as conn:
        # 1. Check if the user is fully registered in the cueuser table.
        is_registered = await user_db.user_exists_by_id(conn, user_id)
        logger.info("auth.status.check.is_registered", result=is_registered)
        if is_registered:
            return "registered"

        # 2. If not registered, check if they have a pending application.
        pending_app = await app_db.get_pending_application_by_user_id(conn, user_id)
        logger.info("auth.status.check.is_pending", result=(pending_app is not None))
        if pending_app:
            return "pending_approval"

    # 3. If neither of the above, the user is new to the system.
    logger.info("auth.status.check.is_unregistered", result=True)
    return "unregistered"
