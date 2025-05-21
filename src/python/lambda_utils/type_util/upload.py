from typing import Optional, List, Dict
from pydantic import BaseModel, Field, PositiveInt, HttpUrl 

# --- For Single File Upload ---
class UploadURLPayload(BaseModel): 
    file_name: str
    checksum: str 
    size: PositiveInt 
    collection: str 
    file_type: str 
    collection_path: Optional[str] = None

class UploadURLResponse(BaseModel): 
    url: str 
    fields: Dict[str, str] 
    s3_key: str 

# NEW: For confirming single upload after client uploads to S3
class ConfirmSingleUploadPayload(BaseModel):
    s3_key: str 
    file_name: str 
    collection: str 
    size_bytes: PositiveInt
    checksum: str 
    file_type: str
    collection_path: Optional[str] = None 
    # s3_etag: Optional[str] = None 

class ConfirmSingleUploadResponse(BaseModel): 
    file_id: str 
    status: str 

# --- For Multipart Upload ---

class MultipartStartRequestPayload(BaseModel):
    file_name: str 
    collection: str 
    upload_target: Optional[str] = None 
    content_type: str 
    overall_checksum: str 

class MultipartStartResponsePayload(BaseModel):
    upload_id: str 
    s3_key: str    

class MultipartGetPartUrlRequestPayload(BaseModel):
    upload_id: str
    part_number: PositiveInt
    file_name: str 
    collection: str 
    checksum: str 
    content_type: str 

class MultipartGetPartUrlResponsePayload(BaseModel):
    presigned_url: str 

class PartInfoPayload(BaseModel):
    PartNumber: PositiveInt
    ETag: str
    ChecksumSHA256: Optional[str] = None 

class MultipartCompleteRequestPayload(BaseModel):
    upload_id: str
    parts: List[PartInfoPayload]
    s3_key: str 
    file_name: str 
    collection: str 
    checksum: str 
    final_file_size: PositiveInt 
    collection_path: Optional[str] = None # Client sends this
    content_type: str # <<< ADDED THIS FIELD

class MultipartCompleteResponsePayload(BaseModel): 
    Location: str 
    Bucket: str
    Key: str 
    ETag: str
    
class MultipartAbortRequestPayload(BaseModel):
    upload_id: str
    s3_key: str 
    file_name: str 
    collection: str
