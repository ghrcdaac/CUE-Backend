from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional, Tuple
from datetime import datetime
from uuid import UUID
from enum import Enum

class ApplicationStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class AccountType(str, Enum):
    daac = "daac"
    provider = "provider"

class UserApplicationBase(BaseModel):
    email: EmailStr
    name: str
    username: str
    justification: str
    ngroup_id: UUID
    account_type: AccountType

    # Example of adding a constraint.
    @field_validator("name")
    def name_must_not_be_empty(cls, value):
        if not value:
            raise ValueError("Name cannot be empty")
        return value

    @field_validator("email")  # Fixed:  Should validate 'email', not 'name'
    def email_must_not_be_empty(cls, value):
        if not value:
            raise ValueError("Email cannot be empty")
        return value


class UserApplicationCreate(UserApplicationBase):
    provider_id: Optional[UUID] = None  # Optional, but conditionally required
    edpub_id: Optional[str] = None  # Add edpub_id (Optional)

    @field_validator("provider_id", mode="before")
    def check_provider_id(cls, value, info):
        if info.data.get('account_type') == AccountType.provider and value is None:
            raise ValueError("provider_id is required when account_type is 'provider'")
        return value


class UserApplicationUpdate(BaseModel):
    # Only status can be updated.  Other fields are not updatable.
    status: Optional[ApplicationStatus] = None

    @field_validator('status', mode="before")  # Corrected validator
    def check_status(cls, value, info):  # Added info argument
        if value and value not in ApplicationStatus:  # Use the Enum!
            raise ValueError(f"Invalid status: {value}.  Must be one of: {[s.value for s in ApplicationStatus]}")
        return value

class UserApplicationReturn(UserApplicationBase):
    id: UUID
    applied: datetime
    status: ApplicationStatus
    provider_id: Optional[UUID] = None
    #added account type
    account_type: AccountType
    edpub_id: Optional[str] = None  # Add edpub_id (Optional)

    @classmethod
    def from_db_row(cls, row: Tuple) -> "UserApplicationReturn":
        # Updated to include edpub_id in the unpacking
        id, email, name, applied, username, status, ngroup_id, provider_id, justification, account_type, edpub_id = row
        return cls(id=id, email=email, name=name, applied=applied, username=username, status=status, ngroup_id=ngroup_id, provider_id=provider_id, justification=justification, account_type=account_type, edpub_id=edpub_id)
    model_config = ConfigDict(populate_by_name=True)