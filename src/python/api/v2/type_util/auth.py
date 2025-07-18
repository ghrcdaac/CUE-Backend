# ==============================================================================
# File: src/python/api/v2/type_util/auth.py (Updated)
# Purpose: Defines Pydantic models for the v2 authentication endpoints.
# New: Added UserStatusResponse model for the login status check.
# ==============================================================================
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal

class TokenIntrospectionRequest(BaseModel):
    """Request body for the token introspection endpoint."""
    token: str
    token_type_hint: Optional[str] = "access_token"

class TokenIntrospectionResponse(BaseModel):
    """Response from the token introspection endpoint."""
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

class UserStatusResponse(BaseModel):
    """
    Response model for the GET /auth/status endpoint.
    Tells the frontend how to proceed after a user logs in.
    """
    status: Literal["registered", "pending_approval", "unregistered"]
