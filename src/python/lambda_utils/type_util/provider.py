from pydantic import BaseModel
from typing import Optional, Tuple
from uuid import UUID

class ProviderBase(BaseModel):
    short_name: str
    long_name: str
    can_upload: Optional[bool] = False

class ProviderCreate(ProviderBase):
    ngroup_id: UUID
    point_of_contact_user_id: UUID

class ProviderUpdate(BaseModel):
    short_name: Optional[str] = None
    long_name: Optional[str] = None
    can_upload: Optional[bool] = None
    point_of_contact_user_id: Optional[UUID] = None

class ProviderReturn(ProviderBase):
    id: UUID
    ngroup_id: UUID
    point_of_contact_user_id: UUID

    @classmethod
    def from_db_row(cls, row: Tuple) -> "ProviderReturn":
        id, ngroup_id, short_name, long_name, can_upload, point_of_contact_user_id = row
        return cls(id=id, ngroup_id=ngroup_id, short_name=short_name, long_name=long_name, can_upload=can_upload, point_of_contact_user_id=point_of_contact_user_id)