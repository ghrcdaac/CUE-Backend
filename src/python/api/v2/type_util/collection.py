# File: src/python/api/v2/type_util/collection.py

from pydantic import BaseModel, Field
from typing import Optional,List
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
    is_deleted: bool = False

    class Config:
        from_attributes = True

class Provider(BaseModel):
    id: UUID
    name: str

class Egress(BaseModel):
    id: UUID
    path: str

class CollectionListResponse(CollectionBase):
    """Model for returning a full collection object from the API."""
    id: UUID
    ngroup_id: UUID
    provider: Optional[Provider] = None
    egress: Optional[Egress] = None

    class Config:
        from_attributes = True

class PaginatedCollectionResponse(BaseModel):
    collections: List[CollectionListResponse]
    page: int
    page_size: int
    total: int