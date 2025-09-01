from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class ApiKeyCreateRequest(BaseModel):
    """Request body for creating a new API key."""
    name: str = Field(..., min_length=3, max_length=100)
    expires_in_days: int = Field(..., gt=0, le=365)
    scopes: List[str] = Field(default=["file:upload"])
    
    # --- Mutually exclusive fields for key owner ---
    target_user_id: Optional[UUID] = None
    proxy_user_name: Optional[str] = Field(None, min_length=3, max_length=100)
    ngroup_id: Optional[UUID] = None # Required if proxy_user_name is set

    @field_validator("proxy_user_name")
    def validate_owner(cls, v, info):
        if v and info.data.get("target_user_id"):
            raise ValueError("target_user_id and proxy_user_name are mutually exclusive.")
        if v and not info.data.get("ngroup_id"):
            raise ValueError("ngroup_id is required when creating a proxy key.")
        return v

class ApiKeyUpdateRequest(BaseModel):
    """Request body for updating an API key's status."""
    is_active: bool

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
    expires_at: datetime
    is_active: bool
    
    # --- Owner Info ---
    user_id: Optional[UUID] = None
    proxy_user_name: Optional[str] = None
    ngroup_id: Optional[UUID] = None
    created_by_user_id: UUID

    class Config:
        from_attributes = True
