from pydantic import BaseModel, EmailStr
from typing import Optional, Tuple
from datetime import datetime
from uuid import UUID

class CueuserBase(BaseModel):
    email: EmailStr
    name: str
    cueusername: str

class CueuserCreate(CueuserBase):
    edpub_id: Optional[str] = None

class CueuserUpdate(CueuserBase):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    cueusername: Optional[str] = None
    edpub_id: Optional[str] = None

class CueuserReturn(CueuserBase):
    id: UUID
    registered: datetime # The database will provide a timezone-aware datetime
    edpub_id: Optional[str] = None

    @classmethod
    def from_db_row(cls, row: Tuple) -> "CueuserReturn":
        id, email, name, registered, cueusername, edpub_id = row
        return cls(id=id, email=email, name=name, registered=registered, cueusername=cueusername, edpub_id=edpub_id)
    
class CueuserAuth(CueuserBase):
    id: UUID
    registered: datetime # The database will provide a timezone-aware datetime
    edpub_id: Optional[str] = None
    ngroup: Optional[str] = None
    role_id: Optional[UUID] = None
    privilages: Optional[list[str]] = None
    
    @classmethod
    def from_db_row(cls, row: Tuple) -> "CueuserReturn":
        id, email, name, registered, cueusername, edpub_id, ngroup, role_id = row
        return cls(id=id, email=email, name=name, registered=registered, cueusername=cueusername, edpub_id=edpub_id, ngroup=ngroup, role_id=role_id)