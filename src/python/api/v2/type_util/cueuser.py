# ==============================================================================
# File: src/python/api/v2/type_util/cueuser.py (Updated)
# Purpose: Defines Pydantic models for the v2 user management API endpoints.
# Change: Updated the UserResponse model to expect a list of ngroup objects.
# ==============================================================================
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
# ---  Import the NgroupListResponse model ---
from .ngroup import NgroupListResponse

# --- User Profile & List Models ---

class UserResponse(BaseModel):
    """A comprehensive user model returned by the API."""
    id: UUID
    email: EmailStr
    name: str
    cueusername: str
    edpub_id: Optional[str] = None
    registered: datetime
    roles: List[str] = Field(default_factory=list, description="List of role short names.")
    # --- The ngroups field is now a list of objects ---
    ngroups: List[NgroupListResponse] = Field(default_factory=list, description="List of ngroup objects the user belongs to.")
    privileges: List[str] = Field(default_factory=list, description="Consolidated list of all permissions.")
    
    class Config:
        from_attributes = True

class UserFindResponse(BaseModel):
    """A simplified user model for search results."""
    id: UUID
    email: EmailStr
    name: str
    cueusername: str
    edpub_id: Optional[str] = None
    registered: datetime
    ngroups: List[str] = Field(default_factory=list) # This can remain as strings for simplicity

    class Config:
        from_attributes = True

# --- User Creation & Update Models ---

class UserCreateRequest(BaseModel):
    """Model for an admin to create a user directly."""
    email: EmailStr
    cueusername: str
    name: str
    role_id: UUID
    ngroup_ids: List[UUID]
    edpub_id: Optional[str] = None

class UserUpdateRequest(BaseModel):
    """Request body for updating a user's details."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    edpub_id: Optional[str] = None
