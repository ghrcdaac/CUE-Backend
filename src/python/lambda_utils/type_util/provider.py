from pydantic import BaseModel
from typing import Optional, Tuple
from uuid import UUID

class ProviderBase(BaseModel):
    short_name: str
    long_name: str
    can_upload: Optional[bool] = False

class ProviderCreate(ProviderBase):
    ngroup_id: UUID
    point_of_contact: UUID

class ProviderUpdate(BaseModel):
    short_name: Optional[str] = None
    long_name: Optional[str] = None
    can_upload: Optional[bool] = None
    point_of_contact: Optional[UUID] = None

class ProviderReturn(ProviderBase):
    id: UUID
    ngroup_id: UUID
    point_of_contact: UUID

    @classmethod
    def from_db_row(cls, row: Tuple) -> "ProviderReturn":
        id, ngroup_id, short_name, long_name, can_upload, point_of_contact = row
        return cls(id=id, ngroup_id=ngroup_id, short_name=short_name, long_name=long_name, can_upload=can_upload, point_of_contact=point_of_contact)
    

class ProviderListReturn(BaseModel):
    id: UUID
    short_name: str

    @classmethod
    def from_db_row(cls, row: Tuple) -> "ProviderListReturn":
        id, _, short_name, *_ = row  # Use _ for values we don't need
        return cls(id=id, short_name=short_name)