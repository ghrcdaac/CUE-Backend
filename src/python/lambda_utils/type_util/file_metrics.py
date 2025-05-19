from pydantic import BaseModel
from typing import Optional, List 
from uuid import UUID
from datetime import datetime


class FileMetricReturnPaginated(BaseModel):
    page: int
    page_size: int

class CostReturn(BaseModel):
    cost: float
    name: Optional[str] = None
    size: Optional[str] = None

class DailyCostReturn(CostReturn):
    date: datetime

class TotalCostReturn(CostReturn):
    start_date: datetime
    end_date: datetime

class FilesMetadata(BaseModel):
    number_of_files: int
    size: str
    cost_per_byte: float

class SummaryCostReturn(BaseModel):
    daily_cost: List[DailyCostReturn]
    total_cost: TotalCostReturn
    files_metadata: FilesMetadata
