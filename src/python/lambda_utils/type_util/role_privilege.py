from pydantic import BaseModel
from typing import Tuple
from uuid import UUID

class RolePrivilegeCreate(BaseModel):
    role_id: UUID
    privilege: str

class RolePrivilegeReturn(BaseModel):
    role_id: UUID
    privilege: str

    @classmethod
    def from_db_row(cls, row: Tuple) -> "RolePrivilegeReturn":
        role_id, privilege = row
        return cls(role_id=role_id, privilege=privilege)