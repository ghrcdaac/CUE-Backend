from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
import json
from datetime import datetime
from lambda_utils.type_util.file_status import MetricsQueryParameters

class ArchiveRequestBody(MetricsQueryParameters):
    """Represents Archive Query Request Body"""
    ngroup_id: UUID

class ArchiveReturn(BaseModel):
    """Represents a row in a Archive Query result"""
    id: UUID
    name: str
    type: str
    checksum: str
    cueuser_uploaded: UUID
    collection_id: UUID
    collection_path: Optional[str] = None
    size_bytes: int
    edpub: bool
    upload_time: datetime
    status: str
    scan_start: Optional[datetime] = None
    scan_end: Optional[datetime] = None
    egress_start: Optional[datetime] = None
    scan_results: Optional[dict] = None
    provider_id: UUID

    @classmethod
    def convert_str(cls,json_object: Dict) -> "ArchiveReturn":
        """Convert fields to their actual data type"""
        for key, value in json_object.items():
            if value == "":
                json_object[key] = None
            if key == "size_bytes":
                json_object[key] = int(value)
            if key == "edpub":
                json_object[key] = bool(value)
            if key == "scan_results":
                json_object[key] = json.loads(value) if value else None
        return cls(**json_object)
