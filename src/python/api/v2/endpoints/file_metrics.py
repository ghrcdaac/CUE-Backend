# File: src/python/api/v2/endpoints/file_metrics.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from uuid import UUID
from typing import List

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser
from v2.utils import file_metrics as metrics_utils
from v2.type_util.file_metrics import (
    MetricsQueryParameters, MetricsSummaryResponse, DailyMetric, OverallMetric, StatusCount,
    CostSummaryResponse, PaginatedCostByCollectionResponse, PaginatedCostByFileResponse
)

router = APIRouter(prefix="/file-metrics", tags=["V2 - File Metrics"])

@router.get("/summary", response_model=MetricsSummaryResponse, dependencies=[Depends(require_privilege("metrics:read"))])
async def get_metrics_summary_endpoint(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    filters: MetricsQueryParameters = Depends()
):
    """Retrieves a comprehensive summary of file metrics for the active ngroup."""
    if not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")

    ngroup_id = UUID(user.active_ngroup_id)
    summary_data = await metrics_utils.get_metrics_summary(request, ngroup_id, filters)
    return MetricsSummaryResponse.model_validate(summary_data)

# --- ADDED: Restored individual metric endpoints from V1 ---

@router.get("/daily-volume", response_model=List[DailyMetric], dependencies=[Depends(require_privilege("metrics:read"))])
async def get_daily_volume_endpoint(request: Request, user: AuthUser = Depends(get_current_user), filters: MetricsQueryParameters = Depends()):
    """Retrieves the daily upload volume for the active ngroup."""
    if not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")
    ngroup_id = UUID(user.active_ngroup_id)
    return await metrics_utils.get_daily_volume(request, ngroup_id, filters)

@router.get("/daily-count", response_model=List[DailyMetric], dependencies=[Depends(require_privilege("metrics:read"))])
async def get_daily_count_endpoint(request: Request, user: AuthUser = Depends(get_current_user), filters: MetricsQueryParameters = Depends()):
    """Retrieves the daily upload count for the active ngroup."""
    if not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")
    ngroup_id = UUID(user.active_ngroup_id)
    return await metrics_utils.get_daily_count(request, ngroup_id, filters)

@router.get("/overall-volume", response_model=OverallMetric, dependencies=[Depends(require_privilege("metrics:read"))])
async def get_overall_volume_endpoint(request: Request, user: AuthUser = Depends(get_current_user), filters: MetricsQueryParameters = Depends()):
    """Retrieves the total upload volume for the active ngroup."""
    if not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")
    ngroup_id = UUID(user.active_ngroup_id)
    return await metrics_utils.get_overall_volume(request, ngroup_id, filters)

@router.get("/overall-count", response_model=OverallMetric, dependencies=[Depends(require_privilege("metrics:read"))])
async def get_overall_count_endpoint(request: Request, user: AuthUser = Depends(get_current_user), filters: MetricsQueryParameters = Depends()):
    """Retrieves the total upload count for the active ngroup."""
    if not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")
    ngroup_id = UUID(user.active_ngroup_id)
    return await metrics_utils.get_overall_count(request, ngroup_id, filters)

@router.get("/status-counts", response_model=List[StatusCount], dependencies=[Depends(require_privilege("metrics:read"))])
async def get_status_counts_endpoint(request: Request, user: AuthUser = Depends(get_current_user), filters: MetricsQueryParameters = Depends()):
    """Retrieves the count of files for each status for the active ngroup."""
    if not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")
    ngroup_id = UUID(user.active_ngroup_id)
    return await metrics_utils.get_status_counts(request, ngroup_id, filters)

# --- Cost metric endpoints remain the same ---

@router.get("/cost-summary", response_model=CostSummaryResponse, dependencies=[Depends(require_privilege("metrics:read"))])
async def get_cost_summary_endpoint(request: Request, user: AuthUser = Depends(get_current_user), filters: MetricsQueryParameters = Depends()):
    if not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")
    ngroup_id = UUID(user.active_ngroup_id)
    return await metrics_utils.get_cost_summary(request, ngroup_id, filters)

@router.get("/cost-by-collection", response_model=PaginatedCostByCollectionResponse, dependencies=[Depends(require_privilege("metrics:read"))])
async def get_cost_by_collection_endpoint(request: Request, user: AuthUser = Depends(get_current_user), filters: MetricsQueryParameters = Depends(), page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100)):
    if not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")
    ngroup_id = UUID(user.active_ngroup_id)
    items, total = await metrics_utils.get_cost_by_collection(request, ngroup_id, filters, page, page_size)
    return PaginatedCostByCollectionResponse(items=items, total=total, page=page, page_size=page_size)

@router.get("/cost-by-file", response_model=PaginatedCostByFileResponse, dependencies=[Depends(require_privilege("metrics:read"))])
async def get_cost_by_file_endpoint(request: Request, user: AuthUser = Depends(get_current_user), filters: MetricsQueryParameters = Depends(), page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100)):
    if not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")
    ngroup_id = UUID(user.active_ngroup_id)
    items, total = await metrics_utils.get_cost_by_file(request, ngroup_id, filters, page, page_size)
    return PaginatedCostByFileResponse(items=items, total=total, page=page, page_size=page_size)