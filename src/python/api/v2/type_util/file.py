from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

class FileResponse(BaseModel):
    id: UUID
    name: str
    type: str
    cueuser_uploaded: UUID
    size_bytes: int
    collection_id: UUID
    collection_path: Optional[str] = None
    checksum: str
    status: Optional[str] = None
    upload_time: Optional[datetime] = None
    scan_start: Optional[datetime] = None
    scan_end: Optional[datetime] = None
    egress_start: Optional[datetime] = None
    scan_results: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True

class PaginatedFileResponse(BaseModel):
    items: List[FileResponse]
    total: int
    page: int
    page_size: int

class FileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    collection_path: Optional[str] = None