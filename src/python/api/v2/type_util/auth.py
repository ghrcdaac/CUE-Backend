# ==============================================================================
# File: src/python/api/v2/type_util/auth.py (Corrected)
# Purpose: Defines Pydantic models specifically for the authentication process endpoints.
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class TokenIntrospectionRequest(BaseModel):
    """Request body for the token introspection endpoint."""
    token: str
    token_type_hint: Optional[str] = "access_token"

class TokenIntrospectionResponse(BaseModel):
    """
    Response from the token introspection endpoint.
    The 'active' field is the most important.
    """
    active: bool
    exp: Optional[int] = None
    iat: Optional[int] = None
    aud: Optional[Any] = None
    iss: Optional[str] = None
    sub: Optional[str] = None
    typ: Optional[str] = None
    azp: Optional[str] = None
    
    class Config:
        extra = "allow"


class LogoutUrlRequest(BaseModel):
    """Request body to get a logout URL."""
    id_token_hint: str = Field(..., description="The ID token of the user session to be logged out.")

class LogoutUrlResponse(BaseModel):
    """Response body containing the fully formed logout URL."""
    logout_url: str
