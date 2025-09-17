from pydantic import BaseModel, UUID4
from typing import Tuple, Optional
from datetime import datetime
from uuid import UUID

class CueuserAuthCreate(BaseModel):
    id: UUID4  # This is the same as the cueuser ID (foreign key)
    refresh_token: str

class CueuserAuthUpdate(BaseModel):
    refresh_token: str

class CueuserAuthReturn(BaseModel):
    id: UUID4
    refresh_token: str
    last_login: datetime

    @classmethod
    def from_db_row(cls, row: Tuple) -> "CueuserAuthReturn":
        id, refresh_token, last_login = row
        return cls(id=id, refresh_token=refresh_token, last_login=last_login)
    
class CueuserAuthBearer(BaseModel):
    id: UUID
    cueusername: str
    edpub_id: Optional[UUID] = None
    ngroup_id: Optional[UUID] = None
    role_short_name: Optional[str] = None
    privileges: Optional[list[str]] = None
    provider_id: Optional[UUID] = None
    
    @classmethod
    def from_db_row(cls, row: Tuple) -> "CueuserAuthBearer":
        id, cueusername, edpub_id, ngroup_id, provider_id, role_short_name, privileges = row
        return cls(id=id, cueusername=cueusername, edpub_id=edpub_id, ngroup_id=ngroup_id, provider_id=provider_id, role_short_name=role_short_name, privileges=privileges)
    