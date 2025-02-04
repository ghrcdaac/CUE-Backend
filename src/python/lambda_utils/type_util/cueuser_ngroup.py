from pydantic import BaseModel
from uuid import UUID
from typing import Tuple

class CueuserNgroupCreate(BaseModel):
    cueuser_id: UUID
    ngroup_id: UUID

class CueuserNgroupReturn(BaseModel):
    cueuser_id: UUID
    ngroup_id: UUID

    @classmethod
    def from_db_row(cls, row: Tuple) -> "CueuserNgroupReturn":
        cueuser_id, ngroup_id = row
        return cls(cueuser_id=cueuser_id, ngroup_id=ngroup_id)