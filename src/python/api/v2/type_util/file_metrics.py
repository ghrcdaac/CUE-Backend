# File: src/python/api/v2/type_util/file_metrics.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from uuid import UUID
from datetime import date
from .file import FileResponse # Import the rich FileResponse model

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

class PaginatedFileStatusResponse(BaseModel):
    items: List[FileResponse] # Uses the rich FileResponse
    total: int
    page: int
    page_size: int

class CostMetric(BaseModel):
    name: str
    size_gb: float
    cost: float

class PaginatedCostResponse(BaseModel):
    items: List[CostMetric]
    total: int
    page: int
    page_size: int