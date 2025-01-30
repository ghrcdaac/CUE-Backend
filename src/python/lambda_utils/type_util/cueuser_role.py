from pydantic import BaseModel
from uuid import UUID
from typing import Tuple

class CueuserRoleCreate(BaseModel):
    cueuser_id: UUID
    role_id: UUID

class CueuserRoleReturn(BaseModel):
    cueuser_id: UUID
    role_id: UUID

    @classmethod
    def from_db_row(cls, row: Tuple) -> "CueuserRoleReturn":
        cueuser_id, role_id = row
        return cls(cueuser_id=cueuser_id, role_id=role_id)