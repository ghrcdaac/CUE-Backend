# File: src/python/api/v2/type_util/upload.py

from pydantic import BaseModel, Field, PositiveInt
from typing import Optional, List, Dict
from uuid import UUID

# --- Single File Upload ---

class PrepareUploadRequest(BaseModel):
    collection_name: str = Field(..., description="The short_name of the collection to upload to.")
    file_name: str = Field(..., description="The original name of the file.")
    file_size_bytes: PositiveInt
    checksum: str
    collection_path: Optional[str] = None
    content_type: str = "application/octet-stream"

class PrepareUploadResponse(BaseModel):
    file_id: UUID
    presigned_url: str

# --- FIX: The CompleteUploadRequest now includes all necessary metadata ---
class CompleteUploadRequest(BaseModel):
    """A single, consolidated model for the 'complete' step."""
    # ID from the prepare step
    file_id: UUID
    
    # All original metadata from the prepare step, needed for validation and DB creation
    collection_name: str
    file_name: str
    file_size_bytes: PositiveInt
    checksum: str
    collection_path: Optional[str] = None
    content_type: str = "application/octet-stream"
    
    # ETag from the S3 upload response
    s3_etag: str

# --- Multipart Upload ---

class MultipartStartRequest(BaseModel):
    collection_name: str
    file_name: str
    content_type: str = "application/octet-stream"
    collection_path: Optional[str] = None

class MultipartStartResponse(BaseModel):
    file_id: UUID
    upload_id: str

class MultipartGetPartUrlRequest(BaseModel):
    file_id: UUID = Field(..., description="The file_id from the 'start' response.")
    upload_id: str
    part_number: PositiveInt

class MultipartGetPartUrlResponse(BaseModel):
    presigned_url: str

class PartInfo(BaseModel):
    PartNumber: PositiveInt
    ETag: str

class MultipartCompleteRequest(BaseModel):
    file_id: UUID = Field(..., description="The file_id from the 'start' response.")
    upload_id: str
    parts: List[PartInfo]
    file_name: str
    collection_name: str
    collection_path: Optional[str] = None
    content_type: str
    checksum: str
    final_file_size: PositiveInt

class MultipartAbortRequest(BaseModel):
    file_id: UUID = Field(..., description="The file_id from the 'start' response.")
    upload_id: str

# --- Generic Success Response ---

class UploadSuccessResponse(BaseModel):
    file_id: UUID
    status: str
    message: str
