from pydantic import BaseModel
from typing import Optional, Tuple
from uuid import UUID

class RoleBase(BaseModel):
    short_name: str
    long_name: str

class RoleCreate(RoleBase):
    pass

class RoleUpdate(RoleBase):
    short_name: Optional[str] = None
    long_name: Optional[str] = None

class RoleReturn(RoleBase):
    id: UUID

    @classmethod
    def from_db_row(cls, row: Tuple) -> "RoleReturn":
        id, short_name, long_name = row
        return cls(id=id, short_name=short_name, long_name=long_name)