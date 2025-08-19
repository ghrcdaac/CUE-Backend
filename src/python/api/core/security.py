# ==============================================================================
# File: src/python/api/core/security.py 
# Purpose: Contains all core logic for authentication and authorization.
# ==============================================================================
import os
import time
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json

import httpx
import structlog
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, jwk
from jose.exceptions import JOSEError
from pydantic import ValidationError
from uuid import UUID

from core.db import get_db_connection
from v2.database_util import cueuser as user_db
from v2.database_util import api_keys as api_key_db
# ---  Import user models from the new type_util file ---
from v2.type_util.auth import AuthUser, AuthenticatedUserClaims

# --- Environment Variables ---
KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER", "https://idfs.uat.earthdatacloud.nasa.gov/realms/cue")
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "cue-uat")
KEYCLOAK_JWKS_URI = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"

# --- Global Cache for JWKS Keys ---
_jwks_cache: Dict[str, Any] = {"keys": [], "expires_at": 0}

logger = structlog.get_logger(__name__)


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

class OIDCValidator:
    """Base class to handle the common JWT validation logic."""
    async def validate_token(self, token: str) -> Dict[str, Any]:
        jwks_keys = await _fetch_jwks_keys()
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid: raise JOSEError("Missing 'kid' in token header")

            rsa_key = next((key for key in jwks_keys if key["kid"] == kid), None)
            if not rsa_key: raise JOSEError("Public key not found for token")

            # --- CHANGE: Added detailed logging for debugging clock skew ---
            unverified_claims = jwt.get_unverified_claims(token)
            token_exp = unverified_claims.get("exp")
            token_iat = unverified_claims.get("iat")
            server_time = time.time()
            leeway = 6000

            logger.info(
                "token.validation.timestamps",
                token_expiration_claim=token_exp,
                token_issued_at_claim=token_iat,
                server_current_time=int(server_time),
                leeway_seconds=leeway,
                token_exp_utc=datetime.fromtimestamp(token_exp, tz=timezone.utc).isoformat() if token_exp else "N/A",
                server_time_utc=datetime.fromtimestamp(server_time, tz=timezone.utc).isoformat(),
                time_difference_seconds=int(server_time - token_exp) if token_exp else "N/A"
            )
            # --- END CHANGE ---

            payload = jwt.decode(
                token, 
                rsa_key, 
                algorithms=["RS256"], 
                audience=KEYCLOAK_AUDIENCE, 
                issuer=KEYCLOAK_ISSUER,
                options={"leeway": leeway}
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.error("token.validation.failed", reason="expired_signature_error", detail="The token has expired according to the validation library.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is expired")
        except jwt.JWTClaimsError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token claims: {e}")
        except (JOSEError, ValidationError) as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")

class OIDCBearer(HTTPBearer, OIDCValidator):
    """
    The main security dependency. Validates the token AND authorizes the user
    by checking for their existence in the local database.
    """
    async def __call__(self, request: Request) -> AuthUser:
        credentials = await super().__call__(request)
        if not credentials or credentials.scheme != "Bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing Bearer token")
        
        payload = await self.validate_token(credentials.credentials)
        user = AuthUser(**payload)

        async with get_db_connection() as conn:
            db_details = await user_db.get_user_auth_details(conn, user.id)
            if not db_details:
                logger.warning("auth.user.not_in_local_db", user_id=str(user.id))
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not registered in this application.")
            
            user.roles = json.loads(db_details.get("roles", "[]"))
            user.privileges = json.loads(db_details.get("privileges", "[]"))
            ngroup_objects = json.loads(db_details.get("ngroups", "[]"))
            user.ngroups = [ng['short_name'] for ng in ngroup_objects]
            user_ngroup_ids = [str(ng['id']) for ng in ngroup_objects]

        active_ngroup_header = request.headers.get("X-Active-Ngroup-Id")
        if active_ngroup_header:
            if active_ngroup_header not in user_ngroup_ids:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have access to the specified ngroup.")
            user.active_ngroup_id = active_ngroup_header

        return user

class OIDCClaimsBearer(HTTPBearer, OIDCValidator):
    """
    A lightweight security dependency that ONLY validates the token.
    It does not check if the user exists in the local database.
    Used for the /auth/status endpoint.
    """
    async def __call__(self, request: Request) -> AuthenticatedUserClaims:
        credentials = await super().__call__(request)
        if not credentials or credentials.scheme != "Bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing Bearer token")
            
        payload = await self.validate_token(credentials.credentials)
        return AuthenticatedUserClaims(**payload)

class APIKeyBearer(HTTPBearer):
    """Security dependency for validating our internal API keys."""
    def __init__(self, required_scopes: List[str]):
        super().__init__()
        self.required_scopes = set(required_scopes)

    async def __call__(self, request: Request) -> AuthUser:
        credentials: Optional[HTTPAuthorizationCredentials] = await super().__call__(request)
        if not credentials or credentials.scheme != "Bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Key")

        api_key = credentials.credentials
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        async with get_db_connection() as conn:
            key_data = await api_key_db.get_user_from_api_key(conn, key_hash)

        if not key_data:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

        key_scopes = set(key_data.get("scopes", []))
        if not self.required_scopes.issubset(key_scopes):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API Key does not have the required permissions.")

        user_id = key_data["user_id"]
        async with get_db_connection() as conn:
            user_profile = await user_db.get_user_by_id(conn, user_id)
            if not user_profile:
                 raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User associated with API Key not found.")
            
            db_details = await user_db.get_user_auth_details(conn, user_id)
            full_profile = {**user_profile, **db_details}
            
            # Manually create the AuthUser object from the combined DB data
            return AuthUser.model_validate(full_profile)

# --- Dependency Instances ---
get_current_user = OIDCBearer()
get_authenticated_user_claims = OIDCClaimsBearer()
get_uploader_user = APIKeyBearer(required_scopes=["file:upload"])

def require_privilege(privilege: str):
    """Dependency factory for checking user privileges."""
    async def privilege_checker(user: AuthUser = Depends(get_current_user)):
        if "admin" in user.roles:
            return # Admins bypass individual privilege checks
        if privilege not in user.privileges:
            logger.warning("authz.failed", required_privilege=privilege, user_id=user.id)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Insufficient privileges: requires '{privilege}'.")
    return privilege_checker
