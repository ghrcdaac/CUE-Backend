# ==============================================================================
# File: src/python/api/v2/utils/keycloak_admin.py (Updated)
# Purpose: Handles all server-to-server communication with the Keycloak Admin API.
# Added validation to ensure required environment variables are set.
# ==============================================================================
import os
import time
import httpx
import structlog
from typing import Dict, Any, Optional
from uuid import UUID

logger = structlog.get_logger(__name__)

class KeycloakAdminClient:
    """A client for interacting with the Keycloak Admin REST API."""
    def __init__(self):
        self.base_url = os.getenv("KEYCLOAK_ISSUER")
        self.client_id = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID")
        self.client_secret = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET")

        # --- CHANGE: Add validation for environment variables ---
        if not all([self.base_url, self.client_id, self.client_secret]):
            raise ValueError(
                "Missing one or more required Keycloak admin environment variables: "
                "KEYCLOAK_ISSUER, KEYCLOAK_ADMIN_CLIENT_ID, KEYCLOAK_ADMIN_CLIENT_SECRET"
            )

        self.token_url = f"{self.base_url}/protocol/openid-connect/token"
        self.admin_api_url = f"{self.base_url.replace('/realms/', '/admin/realms/')}"
        self._access_token: Optional[str] = None
        self._token_expires_at: int = 0

    async def _get_service_token(self) -> str:
        """Gets a service account access token using client_credentials grant."""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        logger.info("keycloak_admin.token.fetching")
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=payload)
            response.raise_for_status()
            token_data = response.json()
            self._access_token = token_data["access_token"]
            self._token_expires_at = time.time() + token_data.get("expires_in", 300) - 30
            return self._access_token

    async def create_user(self, email: str, username: str, first_name: str, last_name: str) -> str:
        """Creates a user in Keycloak and returns the new user's ID."""
        token = await self._get_service_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        user_representation = {
            "username": username,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": True,
            "emailVerified": True,
        }
        users_url = f"{self.admin_api_url}/users"
        
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

    async def delete_user(self, user_id: UUID):
        """Deletes a user from Keycloak."""
        token = await self._get_service_token()
        headers = {"Authorization": f"Bearer {token}"}
        delete_url = f"{self.admin_api_url}/users/{user_id}"
        async with httpx.AsyncClient() as client:
            response = await client.delete(delete_url, headers=headers)
            if response.status_code != 204 and response.status_code != 404:
                logger.error("keycloak_admin.delete.failed", user_id=user_id, status_code=response.status_code)

# Singleton instance for easy dependency injection
keycloak_admin_client = KeycloakAdminClient()

def get_keycloak_admin_client() -> KeycloakAdminClient:
    return keycloak_admin_client
