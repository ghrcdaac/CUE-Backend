from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date

class FileCollectionResponse(BaseModel):
    id: UUID
    name: str

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
    collection: Optional[FileCollectionResponse] = None

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

class FileListRequest(BaseModel):
    """Request body for listing/getting files via API Key."""
    apiKey: str = Field(..., description="The cue_sk_... application API key.")
    file_id: Optional[UUID] = Field(None, description="If provided, fetches this specific file. Otherwise, lists files.")
    status: Optional[str] = None
    page: int = 1
    page_size: int = 50
    start_date: Optional[date] = Field(None, description="Filter for files uploaded on or after this date (YYYY-MM-DD).")
    end_date: Optional[date] = Field(None, description="Filter for files uploaded on or before this date (YYYY-MM-DD).")