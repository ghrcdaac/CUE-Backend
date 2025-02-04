from pydantic import BaseModel, validator, field_validator
from typing import Optional, Tuple
from uuid import UUID
from datetime import datetime

class FileStatusCreate(BaseModel):
    file_id: UUID
    status: str
    scan_results: Optional[dict] = None

    @field_validator('status')
    def check_status(cls, value):
        valid_statuses = ["unscanned", "clean", "infected", "scan_failed", "distributed"]
        if value not in valid_statuses:
            raise ValueError(f"Invalid status: {value}. Must be one of: {valid_statuses}")
        return value

class FileStatusUpdate(BaseModel):
    status: Optional[str] = None
    scan_results: Optional[dict] = None
    scan_start: Optional[datetime] = None
    scan_end: Optional[datetime] = None
    egress_start: Optional[datetime] = None

    @field_validator('status')
    def check_status(cls, value):
        if value:  # Only validate if status is provided
            valid_statuses = ["unscanned", "clean", "infected", "scan_failed", "distributed"]
            if value not in valid_statuses:
                raise ValueError(f"Invalid status: {value}. Must be one of: {valid_statuses}")
        return value

class FileStatusReturn(BaseModel):
    id: UUID
    file_id: UUID
    upload_time: datetime
    scan_start: Optional[datetime] = None
    scan_end: Optional[datetime] = None
    egress_start: Optional[datetime] = None
    status: str
    scan_results: Optional[dict] = None

    @classmethod
    def from_db_row(cls, row: Tuple) -> "FileStatusReturn":
        id, file_id, upload_time, scan_start, scan_end, egress_start, status, scan_results = row
        return cls(
            id=id,
            file_id=file_id,
            upload_time=upload_time,
            scan_start=scan_start,
            scan_end=scan_end,
            egress_start=egress_start,
            status=status,
            scan_results=scan_results
        )