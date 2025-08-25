# File: src/python/api/v2/type_util/egress.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID

class EgressBase(BaseModel):
    """Base model for egress data."""
    type: str
    path: str
    config: Dict[str, Any] = Field(default_factory=dict)

class EgressCreate(EgressBase):
    """Model for creating a new egress target. Ngroup is handled by the endpoint."""
    pass

class EgressUpdate(BaseModel):
    """Model for updating an egress target. All fields are optional."""
    type: Optional[str] = None
    path: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

class EgressResponse(EgressBase):
    """Model for returning a full egress object from the API."""
    id: UUID
    ngroup_id: UUID

    class Config:
        from_attributes = True