from pydantic import BaseModel
from typing import Optional, Tuple, List 
from uuid import UUID
from datetime import datetime

class FileBase(BaseModel):
    name: str
    type: str
    checksum: str

class FileCreate(FileBase):
    cueuser_uploaded: UUID
    collection_id: UUID
    size_bytes: int
    edpub: Optional[bool] = False

class FileUpdate(FileBase):
    name: Optional[str] = None
    type: Optional[str] = None
    checksum: Optional[str] = None
    size_bytes: Optional[int] = None

class FileReturn(FileBase):
    id: UUID
    cueuser_uploaded: UUID
    collection_id: UUID
    size_bytes: int
    edpub: bool

    @classmethod
    def from_db_row(cls, row: Tuple) -> "FileReturn":
        (
            id,
            name,
            file_type,
            cueuser_uploaded,
            size_bytes,
            collection_id,
            edpub,
            checksum
        ) = row
        return cls(
            id=id,
            name=name,
            type=file_type,
            cueuser_uploaded=cueuser_uploaded,
            size_bytes=size_bytes,
            collection_id=collection_id,
            edpub=edpub,
            checksum=checksum
        )

# Added for pagination response in file_status endpoints (can live here or shared types)
class PaginatedFileResponse(BaseModel):
    items: List[FileReturn]
    total: int
    page: int
    page_size: int