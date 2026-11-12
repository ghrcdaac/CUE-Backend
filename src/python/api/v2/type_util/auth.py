# ==============================================================================
# File: src/python/api/v2/type_util/auth.py 
# Purpose: Defines all Pydantic models for the v2 authentication process.
# ==============================================================================
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional, Dict, Any, Literal, List
from uuid import UUID

# --- User Context Models (Used by Security Dependencies) ---

class AuthenticatedUserClaims(BaseModel):
    """Represents the raw, validated claims from a Keycloak JWT."""
    id: UUID = Field(alias="sub")
    email: Optional[EmailStr] = None
    cueusername: Optional[str] = Field(None, alias="preferred_username")
    name: Optional[str] = None
    # Which upstream sign-in Keycloak used (e.g. "launchpad", "google"); signed into the token.
    identity_provider: Optional[str] = None

    class Config:
        populate_by_name = True

class AuthUser(AuthenticatedUserClaims):
    """Represents a fully authorized user, enriched with data from our local DB."""
    first_name: Optional[str] = Field(None, alias="given_name")
    last_name: Optional[str] = Field(None, alias="family_name")
    roles: List[str] = Field(default_factory=list)
    ngroups: List[str] = Field(default_factory=list)
    privileges: List[str] = Field(default_factory=list)
    active_ngroup_id: Optional[str] = None
    # Set when the request used an API key created for one DAAC: uploads and the
    # collection list are limited to that DAAC, admins included (plan 23 B-K1).
    key_ngroup_id: Optional[str] = None

    class Config:
        populate_by_name = True


# --- Initial Login Flow ---

class LoginUrlResponse(BaseModel):
    """Response for the endpoint that provides the Keycloak login URL."""
    login_url: str
    state: str

class CodeExchangeRequest(BaseModel):
    """Request from the frontend callback to exchange the authorization code."""
    code: str
    redirect_uri: str
    state: str

class TokenResponse(BaseModel):
    """
    Response containing the full set of tokens for the frontend.
    The refresh token is now included here.
    """
    access_token: str
    expires_in: int
    id_token: str
    refresh_token: Optional[str] = None
    refresh_expires_in: Optional[int] = None
    token_type: Literal["Bearer"] = "Bearer"

# --- Token Management ---

class RefreshTokenRequest(BaseModel):
    """Request body for the token refresh endpoint."""
    refresh_token: str

class AccessTokenResponse(BaseModel):
    """Response model for the token refresh endpoint."""
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int
    # A new refresh token might be returned if rotation is enabled
    refresh_token: Optional[str] = None

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
    id_token_hint: str

class LogoutUrlResponse(BaseModel):
    """Response body containing the fully formed logout URL."""
    logout_url: str

# --- User Status ---

class UserStatusResponse(BaseModel):
    """Response model for the GET /auth/status endpoint."""
    status: Literal["registered", "pending_approval", "unregistered"]
    # Launchpad gate (APPLICATION_IDP_GATE). provider_only = this login may only apply as a Data Provider.
    idp_gate: Literal["off", "log", "enforce"] = "off"
    provider_only: bool = False

class UserClaimsResponse(BaseModel):
    """A minimal set of user claims for pre-filling registration forms."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    cueusername: Optional[str] = None


# --- Desktop app (CUE GUI) sign-in: PKCE + loopback redirect ---

class DesktopLoginUrlRequest(BaseModel):
    """Body for POST /v2/auth/desktop/login-url."""
    model_config = ConfigDict(extra="forbid")

    redirect_uri: str = Field(..., max_length=200)
    code_challenge: str = Field(..., pattern=r"^[A-Za-z0-9_-]{43}$")
    code_challenge_method: Literal["S256"]
    state: str = Field(..., pattern=r"^[A-Za-z0-9_-]{16,128}$")

class DesktopLoginUrlResponse(BaseModel):
    login_url: str

class DesktopTokenRequest(BaseModel):
    """Body for POST /v2/auth/desktop/token."""
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1, max_length=2048)
    redirect_uri: str = Field(..., max_length=200)
    code_verifier: str = Field(..., pattern=r"^[A-Za-z0-9._~-]{43,128}$")

class DesktopLogoutRequest(BaseModel):
    """Body for POST /v2/auth/desktop/logout."""
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(..., min_length=1, max_length=16384)


class ApiKeyPrincipal(BaseModel):
    """Represents the identity derived from a valid API Key."""
    id: UUID  
    ngroup_id: UUID  
    scopes: List[str] 
    type: str = "api_key"