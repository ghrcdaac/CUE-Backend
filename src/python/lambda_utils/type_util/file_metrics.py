from pydantic import BaseModel
from typing import Optional, List 
from datetime import date
from uuid import UUID
    
class MetricsQueryParameters(BaseModel):
    """Common OPTIONAL query parameters for metric endpoints."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    user_id: Optional[UUID] = None
    collection_id: Optional[UUID] = None
    provider_id: Optional[UUID] = None

class CostReturn(BaseModel):
    """Represents cost of a file/collection"""
    cost: float
    name: Optional[str] = None
    size: Optional[str] = None

class DailyCostReturn(CostReturn):
    """Represents costs on a particular date"""
    date: date

class TotalCostReturn(BaseModel):
    """Represents total cost over the date range between start_date and end_date"""
    cost: float
    start_date: date
    end_date: date

class FilesMetadata(BaseModel):
    """Represents metadata on files included in the cost_summary"""
    number_of_files: int
    size: str
    cost_per_byte: float

class SummaryCostReturn(BaseModel):
    """Represents a cost summary between a date range"""
    daily_cost: List[DailyCostReturn]
    total_cost: TotalCostReturn
    files_metadata: FilesMetadata

class PaginatedReturn(BaseModel):
    costs: List[CostReturn]
    total_count: int