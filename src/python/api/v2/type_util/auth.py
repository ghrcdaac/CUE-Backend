from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr

# --- User & Token Models ---
# The main User model is now in core/security.py

class UserProfileResponse(BaseModel):
    """Data returned from the /users/me endpoint."""
    id: UUID
    email: Optional[EmailStr]
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    roles: List[str]
    privileges: List[str]
    ngroups: List[str]

# --- User Registration Models ---
class UserRegistrationRequest(BaseModel):
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    # Password is not included; it will be set temporarily by the backend.

class UserRegistrationResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    message: str = "User registered successfully. A temporary password has been set."

# --- API Key Models ---
class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., description="A descriptive name for the API key.")

class ApiKeyCreateResponse(BaseModel):
    name: str
    key: str = Field(..., description="The secret API key. This is only shown once.")
    message: str = "Please save this key securely. You will not be ableto see it again."

class ApiKeyInfo(BaseModel):
    id: UUID
    name: str
    prefix: str
    created_at: str
    last_used_at: Optional[str] = None