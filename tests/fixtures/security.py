import os
import json
import hashlib
import base64
from typing import List, Dict, Any, Optional
import uuid

import structlog
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer

from app.v2.database_util import cueuser as user_db
from app.v2.database_util import api_keys as api_key_db
from app.v2.type_util.auth import AuthUser, AuthenticatedUserClaims
from app.v2.utils.cueuser import _parse_user_data

logger = structlog.get_logger(__name__)

class MockOIDCValidator:
    """MOCK Base class to handle the common JWT validation logic."""
    def validate_token(self, request: Request, token: str) -> Dict[str, Any]:
        # mock token - header.payload.signature
        # example - mock_header.{"sub":id, "email":email, "preferred_username":cueusername, "name":name}.mock_signature
        components = token.split(".")
        payload_bytes = base64.b64decode(components[1])
        payload = json.loads(payload_bytes.decode('utf-8'))
        return payload


class OIDCBearer(HTTPBearer, MockOIDCValidator):
    """MOCK The main security dependency. Validates the token AND authorizes the user."""
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


class OIDCClaimsBearer(HTTPBearer, MockOIDCValidator):
    """MOCK A lightweight security dependency that ONLY validates the token."""
    async def __call__(self, request: Request) -> AuthenticatedUserClaims:
        credentials = await super().__call__(request)
        if not credentials or credentials.scheme != "Bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing Bearer token")
        
        payload = self.validate_token(request, credentials.credentials)
        

        return AuthenticatedUserClaims(**payload)

