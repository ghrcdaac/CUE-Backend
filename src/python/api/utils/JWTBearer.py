import os
from typing import Dict, Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwk
from jose.utils import base64url_decode
from starlette.requests import Request
from starlette.status import HTTP_403_FORBIDDEN
from jwt.exceptions import InvalidAlgorithmError, InvalidSignatureError, ExpiredSignatureError, PyJWTError  # Import exceptions

from lambda_utils.type_util.auth import JWKS, JWTAuthorizationCredentials

class JWTBearer(HTTPBearer):
    def __init__(self, jwks: JWKS, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.jwks = jwks
        self.kid_to_jwk = {key["kid"]: key for key in jwks.keys}
        self._region = os.environ.get('AWS_REGION')
        self._pool_id = os.environ.get('POOL_ID')
        self._client_id = os.environ.get('CLIENT_ID')
        if not self._region or not self._pool_id or not self._client_id:
            raise ValueError("AWS_REGION, POOL_ID, and CLIENT_ID must be set in environment variables.")
        self.issuer = f"https://cognito-idp.{self._region}.amazonaws.com/{self._pool_id}"

    def verify_jwk_token(self, jwt_token: str) -> dict:
        """Verifies the JWT token signature, expiration, audience, and issuer."""
        try:
            header = jwt.get_unverified_header(jwt_token)  # Get header *before* decoding
            print(f"JWT Header: {header}")  # DEBUG PRINT
            print(f"self.kid_to_jwk: {self.kid_to_jwk}")  # DEBUG PRINT
            public_key = self.kid_to_jwk[header["kid"]]
        except KeyError:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="JWK public key not found"
            )
        except jwt.exceptions.PyJWTError:  # Use PyJWTError here
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid token")


        key = jwk.construct(public_key)

        try:
            # Verify the signature, audience, and issuer
            payload = jwt.decode(
                jwt_token,
                key=key.to_pem(),  # Convert to PEM format
                algorithms=["RS256"],  # Cognito uses RS256
                audience=self._client_id,  # Validate audience
                issuer=self.issuer  # Validate issuer
            )
            return payload  # Return the decoded payload
        except InvalidSignatureError:  # More specific exceptions first
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid token signature")
        except ExpiredSignatureError: # More specific exceptions first
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Token has expired")
        except InvalidAlgorithmError:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid algorithm")
        except PyJWTError as e:  # Catch any other JWT errors
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=f"Invalid token: {e}")

    async def __call__(self, request: Request) -> Optional[JWTAuthorizationCredentials]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Invalid authentication scheme."
                )
            jwt_token = credentials.credentials
            # Removed message and signature variables.
            try:
                # verify_jwk_token now returns the payload or raises an exception.
                payload = self.verify_jwk_token(jwt_token)
                return JWTAuthorizationCredentials(scheme="Bearer", credentials=jwt_token, claims=payload)  # Pass the jwt_token
            except HTTPException:  # Re-raise HTTP exceptions
                raise
            except Exception as e: # catch other exceptions and raise HTTPException.
                raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=f"Token validation failed: {e}")
        else:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Not authenticated")

class JWTAuthorizationCredentials(HTTPAuthorizationCredentials): # added this class
    # Removed the unnecessary attributes
    #scopes: list[str]
    claims: dict
    def __init__(self, *, scheme: str, credentials: Optional[str] = None,  claims: dict):
        super().__init__(scheme=scheme, credentials=credentials)
        self.claims = claims