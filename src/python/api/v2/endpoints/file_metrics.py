from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Header
from uuid import UUID
from typing import List, Optional

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser
from v2.utils import file_metrics as metrics_utils
from v2.type_util.file_metrics import (
    MetricsQueryParameters, MetricsSummaryResponse, DailyMetric, OverallMetric, StatusCount,
    CostSummaryResponse, PaginatedCostByCollectionResponse, PaginatedCostByFileResponse
)

router = APIRouter(prefix="/file-metrics", tags=["V2 - File Metrics"])

# --- MODIFIED: All endpoints now pass the user and header to the V2 utility functions ---

@router.get("/summary", response_model=MetricsSummaryResponse, dependencies=[Depends(require_privilege("metrics:read"))])
async def get_metrics_summary_endpoint(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    active_ngroup_id: Optional[str] = Header(None, alias="x-active-ngroup-id"),
    filters: MetricsQueryParameters = Depends()
):
    """Retrieves a comprehensive summary of file metrics for the selected ngroup."""
    summary_data = await metrics_utils.get_metrics_summary(request, user, active_ngroup_id, filters)
    return MetricsSummaryResponse.model_validate(summary_data)

@router.get("/daily-volume", response_model=List[DailyMetric], dependencies=[Depends(require_privilege("metrics:read"))])
async def get_daily_volume_endpoint(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    active_ngroup_id: Optional[str] = Header(None, alias="x-active-ngroup-id"),
    filters: MetricsQueryParameters = Depends()
):
    """Retrieves the daily upload volume for the selected ngroup."""
    return await metrics_utils.get_daily_volume(request, user, active_ngroup_id, filters)

@router.get("/daily-count", response_model=List[DailyMetric], dependencies=[Depends(require_privilege("metrics:read"))])
async def get_daily_count_endpoint(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    active_ngroup_id: Optional[str] = Header(None, alias="x-active-ngroup-id"),
    filters: MetricsQueryParameters = Depends()
):
    """Retrieves the daily upload count for the selected ngroup."""
    return await metrics_utils.get_daily_count(request, user, active_ngroup_id, filters)

@router.get("/overall-volume", response_model=OverallMetric, dependencies=[Depends(require_privilege("metrics:read"))])
async def get_overall_volume_endpoint(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    active_ngroup_id: Optional[str] = Header(None, alias="x-active-ngroup-id"),
    filters: MetricsQueryParameters = Depends()
):
    """Retrieves the total upload volume for the selected ngroup."""
    return await metrics_utils.get_overall_volume(request, user, active_ngroup_id, filters)

@router.get("/overall-count", response_model=OverallMetric, dependencies=[Depends(require_privilege("metrics:read"))])
async def get_overall_count_endpoint(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    active_ngroup_id: Optional[str] = Header(None, alias="x-active-ngroup-id"),
    filters: MetricsQueryParameters = Depends()
):
    """Retrieves the total upload count for the selected ngroup."""
    return await metrics_utils.get_overall_count(request, user, active_ngroup_id, filters)

@router.get("/status-counts", response_model=List[StatusCount], dependencies=[Depends(require_privilege("metrics:read"))])
async def get_status_counts_endpoint(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    active_ngroup_id: Optional[str] = Header(None, alias="x-active-ngroup-id"),
    filters: MetricsQueryParameters = Depends()
):
    """Retrieves the count of files for each status for the selected ngroup."""
    return await metrics_utils.get_status_counts(request, user, active_ngroup_id, filters)

# --- V1 Cost endpoints are now mapped to the new V2 utility functions ---
@router.get("/cost-summary", response_model=CostSummaryResponse, dependencies=[Depends(require_privilege("metrics:read"))])
async def get_cost_summary_endpoint(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    active_ngroup_id: Optional[str] = Header(None, alias="x-active-ngroup-id"),
    filters: MetricsQueryParameters = Depends()
):
    """Retrieves cost summary metrics for the selected ngroup, calculated in-app."""
    return await metrics_utils.get_summary_cost(request, user, active_ngroup_id, filters)

@router.get("/cost-by-collection", response_model=PaginatedCostByCollectionResponse, dependencies=[Depends(require_privilege("metrics:read"))])
async def get_cost_by_collection_endpoint(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    active_ngroup_id: Optional[str] = Header(None, alias="x-active-ngroup-id"),
    filters: MetricsQueryParameters = Depends(),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """Retrieves paginated cost by collection for the selected ngroup, calculated in-app."""
    items, total = await metrics_utils.get_cost_by_collection(request, user, active_ngroup_id, filters, page, page_size)
    return PaginatedCostByCollectionResponse(items=items, total=total, page=page, page_size=page_size)

@router.get("/cost-by-file", response_model=PaginatedCostByFileResponse, dependencies=[Depends(require_privilege("metrics:read"))])
async def get_cost_by_file_endpoint(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    active_ngroup_id: Optional[str] = Header(None, alias="x-active-ngroup-id"),
    filters: MetricsQueryParameters = Depends(),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """Retrieves paginated cost by file for the selected ngroup, calculated in-app."""
    items, total = await metrics_utils.get_cost_by_file(request, user, active_ngroup_id, filters, page, page_size)
    return PaginatedCostByFileResponse(items=items, total=total, page=page, page_size=page_size)

