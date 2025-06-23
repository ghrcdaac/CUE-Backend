from fastapi import APIRouter, HTTPException, Query, Depends
from utils.auth import get_current_user_with_ngroup
from utils.file_metrics import get_summary_cost, get_cost_collection, get_cost_file
from lambda_utils.type_util.file_metrics import SummaryCostReturn, PaginatedReturn, MetricsQueryParameters
from uuid import UUID
import logging

router = APIRouter(prefix="/file_metrics", tags=["file_metrics"])
logger = logging.getLogger(__name__)

@router.get("/cost_summary", response_model=SummaryCostReturn)
async def get_cost_summary(
    ngroup_id: UUID = Query(..., description="Mandatory NGROUP ID (DAAC/Org)"),
    params: MetricsQueryParameters = Depends(),
    current_user: dict = Depends(get_current_user_with_ngroup)
):
    """
    Get daily cost, total cost and file metadata for a specific ngroup.
    Filtered, inclusive end date. Auth required
    """
    user_ngroup_id = current_user['ngroup_id']
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized for specified ngroup.")
    try:
        summary_cost =  await get_summary_cost(ngroup_id, params)
        return summary_cost

    except Exception as e:
        logger.error(f"Failed in cost_summary endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error calculating cost summary.")


@router.get("/collection_cost", response_model=PaginatedReturn)
async def get_collection_cost(
    ngroup_id: UUID = Query(..., description="Mandatory NGROUP ID (DAAC/Org)"), 
    params: MetricsQueryParameters = Depends(),
    page: int = Query(1, ge=1 ,description="Page number, starting from 1"),
    page_size: int = Query(10, ge=1, le=200, description="Number of items per page"),
    current_user: dict = Depends(get_current_user_with_ngroup)
):
    """Get cost and size (GB) per collection, filtered, inclusive end date. Auth required."""
    user_ngroup_id = current_user['ngroup_id']
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized for specified ngroup.")
    try:
        collection_cost, total_count, pages = await get_cost_collection(ngroup_id, params, page, page_size)
        return PaginatedReturn(costs=collection_cost, total=total_count, page=page, size=page_size, pages=pages)
    except Exception as e:
        logger.error(f"Failed in collection_cost endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error calculating collection cost.")

@router.get("/file_cost", response_model=PaginatedReturn)
async def get_file_cost(
    ngroup_id: UUID = Query(..., description="Mandatory NGROUP ID (DAAC/Org)"),
    params: MetricsQueryParameters = Depends(),
    page: int = Query(1, ge=1, description="Page number, starting from 1"),
    page_size: int = Query(10, ge=1, le=200, description="Number of items per page"),
    current_user: dict = Depends(get_current_user_with_ngroup)
):
    """Get cost and size (GB) per file, filtered, inclusive end date. Auth required."""
    user_ngroup_id = current_user['ngroup_id']
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized for specified ngroup.")
    try:
        file_cost, total_count, pages = await get_cost_file(ngroup_id, params, page, page_size)
        return PaginatedReturn(costs=file_cost, total=total_count, page=page, size=page_size, pages=pages)
    except Exception as e:
        logger.error(f"Failed in collection_cost endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error calculating collection cost.")