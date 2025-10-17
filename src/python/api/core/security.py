# ==============================================================================
# File: src/python/api/core/security.py
# Purpose: Contains all core logic for authentication and authorization.
# ==============================================================================
import os
import json
import hashlib
from typing import List, Dict, Any, Optional
import uuid


import structlog
from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer
from jose import jwt
from jose.exceptions import JOSEError
from pydantic import ValidationError

from v2.database_util import cueuser as user_db
from v2.database_util import api_keys as api_key_db
from v2.type_util.auth import AuthUser, AuthenticatedUserClaims
from v2.utils.cueuser import _parse_user_data

# --- Environment Variables ---
KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER", "https://idfs.uat.earthdatacloud.nasa.gov/realms/cue")
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "cue-uat")
KEYCLOAK_CERTS_FILE = os.getenv("KEYCLOAK_CERTS_FILE", "idfs_certs_prod.json")

logger = structlog.get_logger(__name__)


def load_jwks_from_file() -> Dict[str, Any]:
    """
    Loads the JWKS keys from the local idfs_certs.json file.
    This is called once during application startup.
    """
    logger.info("jwks.local_file.loading_attempt")
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, KEYCLOAK_CERTS_FILE)
        
        with open(file_path, 'r') as f:
            jwks = json.load(f)
            logger.info("jwks.local_file.loaded_successfully", key_count=len(jwks.get("keys", [])))
            return jwks
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.critical("jwks.local_file.load_failed", error=str(e))
        raise RuntimeError(f"FATAL: Could not load IDFS keys from file: {e}") from e


class OIDCValidator:
    """Base class to handle the common JWT validation logic."""
    def validate_token(self, request: Request, token: str) -> Dict[str, Any]:
        """Validates a JWT using the locally loaded JWKS keys."""
        jwks_keys = request.app.state.jwks_keys.get("keys", [])
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid:
                raise JOSEError("Missing 'kid' in token header")

            rsa_key = next((key for key in jwks_keys if key["kid"] == kid), None)
            if not rsa_key:
                logger.error("jwks.key.not_found", requested_kid=kid)
                raise JOSEError("Public key not found for token. The local JWKS file may be outdated.")

            payload = jwt.decode(
                token, rsa_key, algorithms=["RS256"],
                audience=KEYCLOAK_AUDIENCE, issuer=KEYCLOAK_ISSUER
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.error("token.validation.failed", reason="expired_signature")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is expired")
        except jwt.JWTClaimsError as e:
            logger.error("token.validation.failed", reason="claims_error", error=str(e))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token claims: {e}")
        except (JOSEError, ValidationError) as e:
            logger.error("token.validation.failed", reason="jose_error", error=str(e))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")


class OIDCBearer(HTTPBearer, OIDCValidator):
    """The main security dependency. Validates the token AND authorizes the user."""
    async def __call__(self, request: Request) -> AuthUser:
        credentials = await super().__call__(request)
        if not credentials or credentials.scheme != "Bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing Bearer token")

        payload = self.validate_token(request, credentials.credentials)
        user = AuthUser(**payload)

        # The request.state.pool is attached by the middleware in main.py
        async with request.state.pool.acquire() as conn:
            db_details = await user_db.get_user_auth_details(conn, user.id)
            if not db_details:
                logger.warning("auth.user.not_in_local_db", user_id=str(user.id))
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not registered in this application.")

            user.roles = json.loads(db_details.get("roles", "[]"))
            user.privileges = json.loads(db_details.get("privileges", "[]"))
            ngroup_objects = json.loads(db_details.get("ngroups", "[]"))

            user.ngroups = [str(ng['id']) for ng in ngroup_objects if 'id' in ng]
            user_ngroup_ids = [str(ng['id']) for ng in ngroup_objects if 'id' in ng]

            active_ngroup_header = request.headers.get("X-Active-Ngroup-Id")
            if active_ngroup_header:
                if active_ngroup_header not in user_ngroup_ids:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have access to the specified ngroup.")
                user.active_ngroup_id = active_ngroup_header
        
        return user


class OIDCClaimsBearer(HTTPBearer, OIDCValidator):
    """A lightweight security dependency that ONLY validates the token."""
    async def __call__(self, request: Request) -> AuthenticatedUserClaims:
        credentials = await super().__call__(request)
        if not credentials or credentials.scheme != "Bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing Bearer token")
        
        payload = self.validate_token(request, credentials.credentials)
        

        return AuthenticatedUserClaims(**payload)


class APIKeyBearer(HTTPBearer):
    """Security dependency for validating our internal API keys."""
    def __init__(self, required_scopes: List[str]):
        super().__init__()
        self.required_scopes = set(required_scopes)

    async def __call__(self, request: Request) -> AuthUser:
        credentials = await super().__call__(request)
        if not credentials or credentials.scheme != "Bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Key")

        key_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()

        async with request.state.pool.acquire() as conn:
            key_data = await api_key_db.get_user_from_api_key(conn, key_hash)
            if not key_data:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

            key_scopes = set(key_data.get("scopes", []))
            if not self.required_scopes.issubset(key_scopes):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API Key does not have the required permissions.")

            user_id = key_data.get("user_id")

            # Case 1: The key is associated with a real user.
            if user_id:
                db_details_record = await user_db.get_user_by_id(conn, user_id)
                if not db_details_record:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User associated with API Key not found.")
                
                parsed_details = _parse_user_data(dict(db_details_record))
                
                if parsed_details and 'ngroups' in parsed_details:
                    ngroup_objects = parsed_details['ngroups']
                    parsed_details['ngroups'] = [str(ng['id']) for ng in ngroup_objects if 'id' in ng]

                return AuthUser.model_validate(parsed_details)

            # Case 2: The key is a proxy key.
            else:
                proxy_name = key_data.get("proxy_user_name")
                ngroup_id = key_data.get("ngroup_id")

                if not proxy_name or not ngroup_id:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid proxy key configuration.")

                # Build a synthetic user object for the proxy.
                # The most important part is setting the 'ngroups' correctly.
                proxy_user = AuthUser(
                    id=key_data.get("created_by_user_id"), # Use the creator's ID
                    name=proxy_name,
                    email=f"{proxy_name.lower().replace(' ', '_')}@proxy.internal",
                    roles=["proxy"],
                    privileges=list(key_scopes),
                    ngroups=[str(ngroup_id)] # This authorizes the key for its group
                )
                return proxy_user
           

# --- Dependency Instances ---
get_current_user = OIDCBearer()
get_authenticated_user_claims = OIDCClaimsBearer()
get_uploader_user = APIKeyBearer(required_scopes=["file:upload"])


def require_privilege(privilege: str):
    """Dependency factory for checking user privileges."""
    async def privilege_checker(user: AuthUser = Depends(get_current_user)):
        if "admin" in user.roles:
            return
        if privilege not in user.privileges:
            logger.warning("authz.failed", required_privilege=privilege, user_id=user.id)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Insufficient privileges: requires '{privilege}'.")
    return privilege_checker
