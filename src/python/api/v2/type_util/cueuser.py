# ==============================================================================
# File: src/python/api/v2/type_util/cueuser.py (Refactored)
# Purpose: Defines Pydantic models for the v2 user management API endpoints.
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
    username: str
    edpub_id: Optional[str] = None
    registered: datetime
    roles: List[str] = Field(default_factory=list, description="List of role short names.")
    ngroups: List[str] = Field(default_factory=list, description="List of ngroup short names.")
    
    class Config:
        from_attributes = True # Allows creating model from ORM objects or dicts

# --- User Application Approval ---

class UserApprovalRequest(BaseModel):
    """Request body to approve a user application and create a user."""
    user_application_id: UUID
    role_id: UUID # The role to assign to the new user.
    ngroup_ids: List[UUID] # The ngroups to assign to the new user.

# --- User Update ---

class UserUpdateRequest(BaseModel):
    """Request body for updating a user's details."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    edpub_id: Optional[str] = None

# --- User Creation (Directly by Admin) ---
class UserCreateRequest(BaseModel):
    email: EmailStr
    username: str
    name: str
    role_id: UUID
    ngroup_ids: List[UUID]
    edpub_id: Optional[str] = None

# --- User Find/Search ---
class UserFindResponse(BaseModel):
    """A simplified user model for search results."""
    id: UUID
    email: EmailStr
    name: str
    username: str
    edpub_id: Optional[str] = None
    registered: datetime
    ngroups: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
