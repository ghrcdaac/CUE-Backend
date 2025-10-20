from pydantic import BaseModel
from uuid import UUID
from typing import Tuple

class FileSize(BaseModel):
    """Represents a file's size"""
    id: UUID
    size_bytes: int
    @classmethod
    def from_db_row(cls, row: Tuple) -> "FileSize":
        id, size_bytes = row
        return cls(id=id, size_bytes=size_bytes)

class FileCost(BaseModel):
    """Represents a file's cost metrics"""
    id: UUID
    type: str
    unblended_cost: float
    net_unblended_cost: float
    net_amortized_cost: float
