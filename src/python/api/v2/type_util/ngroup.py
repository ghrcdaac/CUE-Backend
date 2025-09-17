# ==============================================================================
# File: src/python/api/v2/type_util/ngroup.py (Final)
# Purpose: Defines Pydantic models for the v2 ngroup management endpoints.
# ==============================================================================
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class NgroupBase(BaseModel):
    """Base model for ngroup data."""
    short_name: str
    long_name: str

class NgroupCreate(NgroupBase):
    """Model for creating a new ngroup."""
    pass

class NgroupUpdate(BaseModel):
    """Model for updating an existing ngroup. All fields are optional."""
    short_name: Optional[str] = None
    long_name: Optional[str] = None

class NgroupResponse(NgroupBase):
    """Model for returning a full ngroup object from the API."""
    id: UUID

    class Config:
        from_attributes = True

class NgroupListResponse(BaseModel):
    """A simplified model for listing ngroups, used for forms."""
    id: UUID
    short_name: str

    class Config:
        from_attributes = True
