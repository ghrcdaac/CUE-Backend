# ==============================================================================
# File: src/python/api/v2/type_util/api_keys.py (New)
# Purpose: Defines Pydantic models for the API key management endpoints.
# ==============================================================================
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class ApiKeyCreateRequest(BaseModel):
    """Request body for creating a new API key."""
    name: str = Field(..., min_length=3, max_length=100, description="A descriptive name for the API key.")
    # Scopes could be an optional parameter if you want to allow different key types
    scopes: List[str] = Field(default=["file:upload"])

class ApiKeyCreateResponse(BaseModel):
    """Response body after creating a new API key."""
    id: UUID
    name: str
    key: str = Field(..., description="The secret API key. This is only shown once.")
    message: str = "Please save this key securely. You will not be able to see it again."

class ApiKeyInfo(BaseModel):
    """Model representing the details of an API key, excluding the secret."""
    id: UUID
    name: str
    prefix: str
    scopes: List[str]
    created_at: datetime
    last_used_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True
