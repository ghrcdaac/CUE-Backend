# ==============================================================================
# File: src/python/api/core/security.py (Updated)
# Purpose: Adds the API Key validation dependency.
# ==============================================================================
import os
import time
import hashlib
from typing import Optional, List, Dict, Any

import httpx
import structlog
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, jwk
from jose.exceptions import JOSEError
from pydantic import BaseModel, Field, ValidationError
from uuid import UUID

from core.db import get_db_connection
from v2.database_util import cueuser as user_db
from v2.database_util import api_keys as api_key_db

# --- Environment Variables ---
KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER", "https://idfs.sit.earthdatacloud.nasa.gov/realms/cue")
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "cue-uat")
KEYCLOAK_JWKS_URI = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"

# --- Global Cache for JWKS Keys ---
_jwks_cache: Dict[str, Any] = {"keys": [], "expires_at": 0}

logger = structlog.get_logger(__name__)

# --- Pydantic Model for the Authenticated User ---
class User(BaseModel):
    """Represents the authenticated user, parsed from the JWT and enriched from the DB."""
    id: UUID = Field(alias="sub")
    email: Optional[str] = None
    username: Optional[str] = Field(None, alias="preferred_username")
    first_name: Optional[str] = Field(None, alias="given_name")
    last_name: Optional[str] = Field(None, alias="family_name")
    roles: List[str] = Field(default_factory=list)
    ngroups: List[str] = Field(default_factory=list)
    privileges: List[str] = Field(default_factory=list)
    active_ngroup_id: Optional[str] = None

# --- Core Authentication Logic ---

async def _fetch_jwks_keys() -> List[Dict[str, Any]]:
    """Fetches and caches the JWKS public keys from Keycloak."""
    global _jwks_cache
    current_time = time.time()

    if current_time > _jwks_cache["expires_at"]:
        logger.info("jwks.cache.expired", issuer=KEYCLOAK_ISSUER)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(KEYCLOAK_JWKS_URI)
                response.raise_for_status()
                jwks = response.json()
                _jwks_cache = {"keys": jwks["keys"], "expires_at": current_time + 3600}
                logger.info("jwks.cache.refreshed", key_count=len(jwks["keys"]))
        except httpx.HTTPStatusError as e:
            logger.error("jwks.fetch.failed", error=str(e))
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not fetch security keys.")
    
    return _jwks_cache["keys"]

class OIDCBearer(HTTPBearer):
    """A custom security dependency that validates a Keycloak OIDC JWT and enriches the user context."""
    async def __call__(self, request: Request) -> User:
        credentials: Optional[HTTPAuthorizationCredentials] = await super().__call__(request)
        if not credentials or credentials.scheme != "Bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing Bearer token")

        token = credentials.credentials
        jwks_keys = await _fetch_jwks_keys()

        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid: raise JOSEError("Missing 'kid' in token header")

            rsa_key = next((key for key in jwks_keys if key["kid"] == kid), None)
            if not rsa_key: raise JOSEError("Public key not found for token")

            payload = jwt.decode(token, rsa_key, algorithms=["RS256"], audience=KEYCLOAK_AUDIENCE, issuer=KEYCLOAK_ISSUER)
            
            user = User(**payload)
            async with get_db_connection() as conn:
                db_details = await user_db.get_user_auth_details(conn, user.id)
                if db_details:
                    user.roles = db_details.get("roles", [])
                    user.ngroups = db_details.get("ngroups", [])
                    user.privileges = db_details.get("privileges", [])

            active_ngroup_header = request.headers.get("X-Active-Ngroup-Id")
            if active_ngroup_header:
                if active_ngroup_header not in user.ngroups:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have access to the specified ngroup.")
                user.active_ngroup_id = active_ngroup_header

            return user

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is expired")
        except (JOSEError, ValidationError) as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")

class APIKeyBearer(HTTPBearer):
    """Security dependency for validating our internal API keys."""
    def __init__(self, required_scopes: List[str]):
        super().__init__()
        self.required_scopes = set(required_scopes)

    async def __call__(self, request: Request) -> User:
        credentials: Optional[HTTPAuthorizationCredentials] = await super().__call__(request)
        if not credentials or credentials.scheme != "Bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Key")

        api_key = credentials.credentials
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        async with get_db_connection() as conn:
            key_data = await api_key_db.get_user_from_api_key(conn, key_hash)

        if not key_data:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

        # Check if the key has the required scopes
        key_scopes = set(key_data.get("scopes", []))
        if not self.required_scopes.issubset(key_scopes):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API Key does not have the required permissions.")

        # Key is valid, now fetch the user's full details for context
        user_id = key_data["user_id"]
        async with get_db_connection() as conn:
            user_profile = await user_db.get_user_by_id(conn, user_id)
        
        if not user_profile:
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User associated with API Key not found.")

        return User.model_validate(user_profile)


# --- Dependency Instances ---
get_current_user = OIDCBearer()
get_uploader_user = APIKeyBearer(required_scopes=["file:upload"]) # For upload endpoints

def require_privilege(privilege: str):
    """Dependency factory for checking user privileges."""
    async def privilege_checker(user: User = Depends(get_current_user)):
        if "admin" not in user.roles and privilege not in user.privileges:
            logger.warning("authz.failed", required_privilege=privilege, user_id=user.id)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Insufficient privileges: requires '{privilege}'.")
    return privilege_checker
