from pydantic import BaseModel
from typing import Optional, Tuple, List
from uuid import UUID
from .file import FileReturn


class CollectionBase(BaseModel):
    short_name: str
    active: Optional[bool] = False

class CollectionCreate(CollectionBase):
    ngroup_id: UUID
    egress_id: UUID
    provider_id: UUID

class PaginatedFiles(BaseModel):
    files: List[FileReturn]
    total_count: int

class CollectionUpdate(CollectionBase):
    short_name: Optional[str] = None
    active: Optional[bool] = None

class CollectionReturn(CollectionBase):
    id: UUID
    ngroup_id: UUID
    egress_id: UUID
    provider_id: UUID

    @classmethod
    def from_db_row(cls, row: Tuple) -> "CollectionReturn":
        id, ngroup_id, egress_id, short_name, provider_id, active = row
        return cls(id=id, ngroup_id=ngroup_id, egress_id=egress_id, short_name=short_name, provider_id=provider_id, active=active)