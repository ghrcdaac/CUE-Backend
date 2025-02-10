from pydantic import BaseModel, EmailStr, validator
from typing import Optional, Tuple
from uuid import UUID
from datetime import datetime

class UserApplicationBase(BaseModel):
    email: EmailStr
    name: str
    username: str
    justification: str

class UserApplicationCreate(UserApplicationBase):
    ngroup_id: UUID
    status: Optional[str] = 'pending'  # Make status optional and set default

class UserApplicationUpdate(BaseModel):
    status: Optional[str] = None

    @validator('status')
    def validate_status(cls, value):
        valid_statuses = ['pending', 'approved', 'rejected']
        if value not in valid_statuses:
            raise ValueError(f"Invalid status: {value}. Must be one of: {valid_statuses}")
        return value

class UserApplicationReturn(UserApplicationBase):
    id: UUID
    applied: datetime
    status: str
    ngroup_id: UUID

    @classmethod
    def from_db_row(cls, row: Tuple) -> "UserApplicationReturn":
        id, email, name, applied, username, status, ngroup_id, justification = row
        return cls(id=id, email=email, name=name, applied=applied, username=username, status=status, ngroup_id=ngroup_id, justification=justification)