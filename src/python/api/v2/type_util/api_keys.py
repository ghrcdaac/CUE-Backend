# v2/type_util/api_keys.py

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, model_validator

class ApiKeyCreateRequest(BaseModel):
    """Request body for creating a new API key."""
    name: str = Field(..., min_length=3, max_length=100)
    scopes: List[str] = Field(default=["file:upload"])
    
    # --- Expiration fields to support custom dates ---
    expires_in_days: Optional[int] = Field(None, gt=0, le=365)
    expires_at: Optional[datetime] = None
    
    # --- Owner fields ---
    target_user_id: Optional[UUID] = None
    proxy_user_name: Optional[str] = Field(None, min_length=3, max_length=100)
    ngroup_id: Optional[UUID] = None

    # Validator to ensure expiration is handled correctly
    @model_validator(mode='after')
    def validate_expiration(self):
        if self.expires_in_days is None and self.expires_at is None:
            raise ValueError("Either 'expires_in_days' or 'expires_at' must be provided.")
        if self.expires_in_days is not None and self.expires_at is not None:
            raise ValueError("'expires_in_days' and 'expires_at' are mutually exclusive.")
        return self

    # Validator to ensure owner is handled correctly
    @model_validator(mode='after')
    def validate_owner(self):
        if self.proxy_user_name and self.target_user_id:
            raise ValueError("target_user_id and proxy_user_name are mutually exclusive.")
        if self.proxy_user_name and not self.ngroup_id:
            raise ValueError("ngroup_id is required when creating a proxy key.")
        return self

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
    key_display_suffix: Optional[str] = None
    last_used_at: Optional[datetime] = None  # Added
    
    # --- Owner Info ---
    user_id: Optional[UUID] = None
    proxy_user_name: Optional[str] = None
    ngroup_id: Optional[UUID] = None
    created_by_user_id: UUID

    user_name: Optional[str] = None
    created_by_user_name: Optional[str] = None

    class Config:
        from_attributes = True