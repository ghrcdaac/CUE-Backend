import json
from pydantic import BaseModel, field_validator, Field
from typing import Optional, Tuple, List, Dict
from uuid import UUID
from datetime import datetime, timezone, date



class MetricsQueryParameters(BaseModel):
    """Common OPTIONAL query parameters for metric endpoints."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None 
    user_id: Optional[UUID] = None
    collection_id: Optional[UUID] = None
    provider_id: Optional[UUID] = None

class DailyMetricItem(BaseModel):
    """Represents a single day's metric value."""
    day: date
    value: float

class OverallMetricResult(BaseModel):
    """Represents the overall metric value."""
    value: float
    start_date: Optional[date] = None
    end_date: Optional[date] = None



class FileStatusCreate(BaseModel):
    id: UUID
    status: str
    scan_results: Optional[dict] = None
    

    @field_validator('status')
    def check_status_create(cls, value):
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
    def check_status_update(cls, value):
        valid_statuses = ["unscanned", "clean", "infected", "scan_failed", "distributed"]
        if value and value not in valid_statuses:
             raise ValueError(f"Invalid status:{value}. Must be one of: {valid_statuses}")
        return value

class FileStatusReturn(BaseModel):
    id: UUID
    upload_time: datetime
    scan_start: Optional[datetime] = None
    scan_end: Optional[datetime] = None
    egress_start: Optional[datetime] = None
    status: str
    scan_results: Optional[dict] = None

    @classmethod
    def from_db_row(cls, row: Tuple) -> "FileStatusReturn":
        id, upload_time, scan_start, scan_end, egress_start, status, scan_results_str = row
        scan_results = json.loads(scan_results_str) if scan_results_str else None

        return cls(id=id, upload_time=upload_time, scan_start=scan_start,
                   scan_end=scan_end, egress_start=egress_start, status=status,
                   scan_results=scan_results)
    class Config:
        populate_by_name = True 

class PaginatedFileResponse(BaseModel):
    items: List[FileStatusReturn]
    total: int
    page: int
    page_size: int