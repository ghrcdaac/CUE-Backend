# ==============================================================================
# File: src/python/api/v2/type_util/role.py (Final)
# Purpose: Defines Pydantic models for the v2 role management endpoints.
# ==============================================================================
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class RoleBase(BaseModel):
    """Base model for role data."""
    short_name: str
    long_name: str

class RoleCreate(RoleBase):
    """Model for creating a new role."""
    pass

class RoleUpdate(BaseModel):
    """Model for updating an existing role. All fields are optional."""
    short_name: Optional[str] = None
    long_name: Optional[str] = None

class RoleResponse(RoleBase):
    """Model for returning a full role object from the API."""
    id: UUID

    class Config:
        from_attributes = True
