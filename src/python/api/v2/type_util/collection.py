# File: src/python/api/v2/type_util/collection.py

from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID

class CollectionBase(BaseModel):
    """Base model for collection data."""
    short_name: str
    active: bool = False

class CollectionCreate(CollectionBase):
    """Model for creating a new collection."""
    provider_id: UUID
    egress_id: UUID
    # Ngroup_id is not included here as it will be inferred from the user's session.

class CollectionUpdate(BaseModel):
    """Model for updating a collection. All fields are optional."""
    short_name: Optional[str] = None
    active: Optional[bool] = None
    provider_id: Optional[UUID] = None
    egress_id: Optional[UUID] = None

class CollectionResponse(CollectionBase):
    """Model for returning a full collection object from the API."""
    id: UUID
    ngroup_id: UUID
    provider_id: UUID
    egress_id: UUID

    class Config:
        from_attributes = True

class PaginatedCollectionReturn(BaseModel):
    total_count: int
    collections: List[CollectionResponse]

class CollectionFileCount(BaseModel):
    id: UUID
    name: str
    file_count: int

class CollectionFileResponse(BaseModel):
    ngroup_id: UUID
    page: int
    total_count: int
    files_by_count:List[CollectionFileCount]