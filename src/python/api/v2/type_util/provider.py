# ==============================================================================
# File: src/python/api/v2/type_util/provider.py (Final)
# Purpose: Defines Pydantic models for the v2 provider management endpoints.
# ==============================================================================
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class ProviderBase(BaseModel):
    """Base model for provider data."""
    short_name: str
    long_name: str
    can_upload: bool = False
    reason : Optional[str] = None

class ProviderCreate(ProviderBase):
    """Model for creating a new provider."""
    ngroup_id: UUID
    point_of_contact: UUID

class ProviderUpdate(BaseModel):
    """Model for updating an existing provider. All fields are optional."""
    short_name: Optional[str] = None
    long_name: Optional[str] = None
    can_upload: Optional[bool] = None
    point_of_contact: Optional[UUID] = None
    reason: Optional[str] = None

class ProviderResponse(ProviderBase):
    """Model for returning a full provider object from the API."""
    id: UUID
    ngroup_id: UUID
    point_of_contact: UUID
    reason:  Optional[str] = None

    class Config:
        from_attributes = True

class ProviderListResponse(BaseModel):
    """A simplified model for listing providers, used for forms."""
    id: UUID
    short_name: str

    class Config:
        from_attributes = True
