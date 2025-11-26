# v2/type_util/api_keys.py

from typing import Optional, List, Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, model_validator

class ApiKeyCreateRequest(BaseModel):
    """Request body for creating a new API key."""
    name: str = Field(..., min_length=3, max_length=100)
    
    #The client must now explicitly state the type of key being created.
    key_type: Literal['personal', 'managed_user', 'proxy'] = Field(..., 
        description="The type of key to create.")
    
    scopes: List[str] = Field(default=["file:upload"])
    
    # --- Expiration fields ---
    expires_in_days: Optional[int] = Field(None, gt=0, le=365)
    expires_at: Optional[datetime] = None
    
    # --- Owner fields (conditionally required based on key_type) ---
    target_user_id: Optional[UUID] = None
    proxy_user_name: Optional[str] = Field(None, min_length=3, max_length=100)
    ngroup_id: Optional[UUID] = None

    @model_validator(mode='after')
    def validate_expiration(self):
        """Validator to ensure expiration is handled correctly."""
        if self.expires_in_days is None and self.expires_at is None:
            raise ValueError("Either 'expires_in_days' or 'expires_at' must be provided.")
        if self.expires_in_days is not None and self.expires_at is not None:
            raise ValueError("'expires_in_days' and 'expires_at' are mutually exclusive.")
        return self

    # Validator is now simpler and more explicit
    @model_validator(mode='after')
    def validate_owner_by_type(self):
        """Validator to ensure the correct fields are provided for the given key_type."""
        if self.key_type == 'personal':
            # A personal key MUST be associated with a group.
            if not self.ngroup_id:
                raise ValueError("For 'personal' keys, the 'ngroup_id' is required.")
            if self.target_user_id or self.proxy_user_name:
                raise ValueError("For 'personal' keys, do not provide 'target_user_id' or 'proxy_user_name'.")
        
        elif self.key_type == 'managed_user':
            if not self.target_user_id or not self.ngroup_id:
                raise ValueError("For 'managed_user' keys, 'target_user_id' and 'ngroup_id' are required.")
            if self.proxy_user_name:
                raise ValueError("'proxy_user_name' must not be set for 'managed_user' keys.")

        elif self.key_type == 'proxy':
            if not self.proxy_user_name or not self.ngroup_id:
                raise ValueError("For 'proxy' keys, 'proxy_user_name' and 'ngroup_id' are required.")
            if self.target_user_id:
                raise ValueError("'target_user_id' must not be set for 'proxy' keys.")
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
    
    # Added key_type to the response model.
    key_type: str
    
    scopes: List[str]
    created_at: datetime
    expires_at: datetime
    is_active: bool
    key_display_suffix: Optional[str] = None
    last_used_at: Optional[datetime] = None
    
    # --- Owner Info ---
    user_id: Optional[UUID] = None
    proxy_user_name: Optional[str] = None
    ngroup_id: Optional[UUID] = None
    created_by_user_id: UUID

    user_name: Optional[str] = None
    created_by_user_name: Optional[str] = None

    class Config:
        from_attributes = True

class PaginatedAPIKeyResponse(BaseModel):
    api_keys: List[ApiKeyInfo]
    page: int
    page_size: int
    total: int