# ==============================================================================
# File: src/python/api/v2/type_util/user_application.py (Final)
# Purpose: Defines Pydantic models for the v2 user application process.
# ==============================================================================
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum

class ApplicationStatus(str, Enum):
    """Enum for the status of a user application."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class AccountType(str, Enum):
    """Enum for the type of account being applied for."""
    DAAC = "daac"
    PROVIDER = "provider"

class UserApplicationCreate(BaseModel):
    """Model for submitting a new user application. The user_id comes from the token, not the body."""
    email: EmailStr
    name: str
    username: str
    justification: str
    ngroup_id: UUID
    account_type: AccountType
    provider_id: Optional[UUID] = None
    edpub_id: Optional[str] = None

    @field_validator("provider_id", mode="before")
    def check_provider_id(cls, v, info):
        # Pydantic v2 uses info.data to get the model's data
        if info.data.get('account_type') == AccountType.PROVIDER and v is None:
            raise ValueError("provider_id is required when account_type is 'provider'")
        return v

class UserApplicationUpdate(BaseModel):
    """Model for an admin to update the status of an application (approval/rejection)."""
    status: ApplicationStatus
    
class UserApplicationResponse(BaseModel):
    """Model for returning user application data from the API."""
    id: UUID
    user_id: UUID # The applicant's Keycloak ID
    email: EmailStr
    name: str
    username: str
    justification: str
    ngroup_id: UUID
    provider_id: Optional[UUID] = None
    account_type: AccountType
    edpub_id: Optional[str] = None
    status: ApplicationStatus
    applied: datetime

    class Config:
        from_attributes = True
