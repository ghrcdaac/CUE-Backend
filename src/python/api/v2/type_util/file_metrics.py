# File: src/python/api/v2/type_util/metrics.py

from pydantic import BaseModel
from typing import Optional, List, Dict
from uuid import UUID
from datetime import date
from .file import FileResponse

class MetricsQueryParameters(BaseModel):
    """Optional query parameters for filtering metric endpoints."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    user_id: Optional[UUID] = None
    collection_id: Optional[UUID] = None
    provider_id: Optional[UUID] = None

class DailyMetric(BaseModel):
    day: date
    value: float

class OverallMetric(BaseModel):
    value: float

class StatusCount(BaseModel):
    status: str
    count: int

class MetricsSummaryResponse(BaseModel):
    daily_volume: List[DailyMetric]
    daily_count: List[DailyMetric]
    overall_volume: OverallMetric
    overall_count: OverallMetric
    status_counts: List[StatusCount]

class CostSummaryResponse(BaseModel):
    daily_cost: List[DailyMetric]
    total_cost: OverallMetric
    total_files: int
    total_size_gb: float

class CostByCollectionItem(BaseModel):
    name: str
    size_gb: float
    cost: float

class PaginatedCostByCollectionResponse(BaseModel):
    items: List[CostByCollectionItem]
    total: int
    page: int
    page_size: int

class CostByFileItem(BaseModel):
    name: str
    size_gb: float
    cost: float

class PaginatedCostByFileResponse(BaseModel):
    items: List[CostByFileItem]
    total: int
    page: int
    page_size: int