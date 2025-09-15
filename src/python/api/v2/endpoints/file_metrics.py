# ==============================================================================
# File: src/python/api/v2/endpoints/file_metrics.py (Updated)
# --- MODIFIED to pass the request object down to the utility layer ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request # <-- Import Request
from uuid import UUID
from typing import List

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser
from v2.utils import file_metrics as metrics_utils
from v2.type_util.file_metrics import (
    MetricsQueryParameters, MetricsSummaryResponse,
    PaginatedFileStatusResponse, PaginatedCostResponse
)

router = APIRouter(prefix="/file-metrics", tags=["V2 - File Metrics"])

# --- MODIFIED: All endpoints now accept `request: Request` ---

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
    try:
        summary_data = await metrics_utils.get_metrics_summary(request, ngroup_id, filters)
        return MetricsSummaryResponse.model_validate(summary_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/list-by-status", response_model=PaginatedFileStatusResponse, dependencies=[Depends(require_privilege("file:read"))])
async def list_files_by_status_endpoint(
    request: Request,
    status: str = Query(..., description="File status to filter by (e.g., 'infected', 'clean')."),
    user: AuthUser = Depends(get_current_user),
    filters: MetricsQueryParameters = Depends(),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """Lists files for the active ngroup, filtered by status, with pagination."""
    if not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")

    ngroup_id = UUID(user.active_ngroup_id)
    try:
        items, total = await metrics_utils.list_files_by_status(request, ngroup_id, status, filters, page, page_size)
        return PaginatedFileStatusResponse(items=items, total=total, page=page, page_size=page_size)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/cost-by-collection", response_model=PaginatedCostResponse, dependencies=[Depends(require_privilege("metrics:read"))])
async def get_cost_by_collection_endpoint(
    request: Request,
    user: AuthUser = Depends(get_current_user),
    filters: MetricsQueryParameters = Depends(),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """Retrieves cost metrics aggregated by collection for the active ngroup."""
    if not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")
    
    ngroup_id = UUID(user.active_ngroup_id)
    try:
        items, total = await metrics_utils.get_cost_by_collection(request, ngroup_id, filters, page, page_size)
        return PaginatedCostResponse(items=items, total=total, page=page, page_size=page_size)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
