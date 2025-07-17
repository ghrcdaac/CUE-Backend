# ==============================================================================
# File: src/python/api/v2/type_util/cueuser.py (Refactored)
# Purpose: Defines Pydantic models for the v2 user management API endpoints.
# Change: Standardized on 'cueusername' instead of 'username'.
# ==============================================================================
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

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
    ngroups: List[str] = Field(default_factory=list, description="List of ngroup short names.")
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
    ngroups: List[str] = Field(default_factory=list)

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
