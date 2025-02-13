from pydantic import BaseModel, SecretStr
from typing import Dict, Any, Optional, List

# We *don't* need login/password models on the backend with USER_SRP_AUTH
# No LoginRequest
# No PwdResponse

class AuthResponse(BaseModel):  # For returning tokens
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None  #For refresh token
    id_token: Optional[str] = None

class RefreshTokenRequest(BaseModel): # Pydantic model for refresh token
    refresh_token: str

# Simplified JWKS model (expand as needed)
JWK = Dict[str, str]  # Each key in the JWKS is a dictionary

class JWKS(BaseModel):
    keys: List[JWK]

# For JWT authorization
class JWTAuthorizationCredentials():
        #scopes: list[str] #Removed this attribute
        claims: dict
        def __init__(self, claims: dict):
            self.claims = claims

class TokenVerificationRequest(BaseModel):
    token: str  # The JWT to verify