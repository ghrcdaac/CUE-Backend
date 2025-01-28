from pydantic import BaseModel, UUID4
from typing import Tuple, Optional
from uuid import UUID

class NgroupCreate(BaseModel):
    id: Optional[UUID4] = None
    short_name: str
    long_name: str

class NgroupReturn(NgroupCreate):
    id: UUID4

    @classmethod
    def from_db_row(cls, row: Tuple) -> "NgroupReturn":
        """Factory function to create an NgroupReturn instance from a database row."""
        id, short_name, long_name = row
        return cls(id=id, short_name=short_name, long_name=long_name)

class NgroupUpdate(BaseModel):
    short_name: Optional[str] = None
    long_name: Optional[str] = None