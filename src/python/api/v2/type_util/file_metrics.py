# File: src/python/api/v2/type_util/file_metrics.py

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import date

class MetricsQueryParameters(BaseModel):
    """Optional query parameters for filtering metric endpoints."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    user_id: Optional[UUID] = None
    collection_id: Optional[UUID] = None
    provider_id: Optional[UUID] = None


class DailyMetric(BaseModel):
    day: date
    value: int


class OverallMetric(BaseModel):
    value: int

class StatusCount(BaseModel):
    status: str
    count: int

class MetricsSummaryResponse(BaseModel):
    daily_volume: List[DailyMetric]
    daily_count: List[DailyMetric]
    overall_volume: OverallMetric
    overall_count: OverallMetric
    status_counts: List[StatusCount]


class DailyCostMetric(BaseModel):
    day: date
    value: float

class OverallCostMetric(BaseModel):
    value: float



class CostSummaryResponse(BaseModel):
    daily_cost: List[DailyCostMetric]
    total_cost: OverallCostMetric
    total_files: int
    total_size_bytes: int

class CostByCollectionItem(BaseModel):
    name: str
    size_bytes: int
    cost: float

class PaginatedCostByCollectionResponse(BaseModel):
    items: List[CostByCollectionItem]
    total: int
    page: int
    page_size: int

class CostByFileItem(BaseModel):
    name: str
    size_bytes: int
    cost: float

class PaginatedCostByFileResponse(BaseModel):
    items: List[CostByFileItem]
    total: int
    page: int
    page_size: int