# ==============================================================================
# File: src/python/api/v2/type_util/upload.py
# ==============================================================================
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

class CompleteUploadRequest(BaseModel):
    """A simplified, lightweight model for the 'complete' step."""
    file_id: UUID = Field(..., description="The file_id from the 'prepare' response.")
    s3_etag: str = Field(..., description="The ETag from the successful S3 upload response header.")

# --- Multipart Upload ---

class MultipartStartRequest(BaseModel):
    collection_name: str
    file_name: str
    content_type: str = "application/octet-stream"
    collection_path: Optional[str] = None
    checksum: Optional[str] = Field(None, description="The file's final checksum, if known in advance.")
    final_file_size: Optional[PositiveInt] = Field(None, description="The file's final size in bytes, if known in advance.")

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

