from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Tuple, List
from datetime import datetime
from uuid import UUID

class CueuserBase(BaseModel):
    email: EmailStr
    name: str
    cueusername: str

class CueuserCreate(CueuserBase):
    edpub_id: Optional[str] = None
    ngroup_id: UUID = None # Add ngroup ID here
    account_type: str = None
    provider_id: Optional[UUID] = None
    role_id: Optional[UUID] = None # Add Role Id

    @field_validator("account_type")
    def validate_account_type(cls, value):
      valid_types = ["daac", "provider"]
      if value not in valid_types:
            raise ValueError(f"Invalid status: {value}. Must be one of: {valid_types}")
      return value

    @field_validator("provider_id", mode="before")
    def check_provider_id(cls, value, values):
        if 'account_type' in values and values['account_type'] == "provider" and value is None:
            raise ValueError("provider_id is required when account_type is 'provider'")
        return value
class CueuserUpdate(CueuserBase):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    cueusername: Optional[str] = None
    edpub_id: Optional[str] = None

class CueuserReturn(CueuserBase):
    id: UUID
    registered: datetime  # The database will provide a timezone-aware datetime
    edpub_id: Optional[str] = None
    class Config:
        from_attributes = True

    @classmethod
    def from_db_row(cls, row: Tuple) -> "CueuserReturn":
        id, email, name, registered, cueusername, edpub_id = row
        return cls(id=id, email=email, name=name, registered=registered, cueusername=cueusername, edpub_id=edpub_id)

# Added CueuserAuth Model
class CueuserAuth(CueuserReturn):  # Inherit from CueuserReturn
    ngroup: Optional[str] = None  # Use Optional[str] for ngroup short_name
    role_name: Optional[str] = None # Use role name, not role_id
    privileges: Optional[List[str]] = None

    @classmethod
    def from_db_row(cls, row: Tuple) -> "CueuserAuth":
        id, email, name, registered, cueusername, edpub_id, ngroup, role_name = row
        return cls(id=id, email=email, name=name, registered=registered,
                   cueusername=cueusername, edpub_id=edpub_id,
                   ngroup=ngroup, role_name=role_name) # Include in the constructor