from pydantic import BaseModel
from uuid import UUID
from typing import Tuple

class CueuserProviderCreate(BaseModel):
    cueuser_id: UUID
    provider_id: UUID

class CueuserProviderReturn(BaseModel):
    cueuser_id: UUID
    provider_id: UUID

    @classmethod
    def from_db_row(cls, row: Tuple) -> "CueuserProviderReturn":
        cueuser_id, provider_id = row
        return cls(cueuser_id=cueuser_id, provider_id=provider_id)