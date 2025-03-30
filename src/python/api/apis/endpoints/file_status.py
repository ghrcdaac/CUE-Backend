# endpoints/file_status.py

from fastapi import APIRouter, HTTPException, Depends, Query
from uuid import UUID
from typing import List, Dict
from datetime import date
import logging

# --- Import Authentication ---
# Import the NEW dependency function
from utils.auth import get_current_user_with_ngroup, get_cognito_auth # Keep old one if needed elsewhere

# --- Import utils and types ---
from utils.file_status import (create_file_status,
                               delete_file_status,
                               get_file_status,
                               list_file_statuses, get_file_status_counts, list_files_by_status,
                               FileStatusNotFoundError, update_file_status,
                               AuthorizationError)
from utils.file import get_ngroup_id_for_file, FileNotFoundError as BaseFileNotFoundError

from lambda_utils.type_util.file_status import (FileStatusCreate,
                                               FileStatusReturn,
                                               FileStatusUpdate, PaginatedFileResponse, FileStatusMetricsSummary  )


from utils.file_status import (
    calculate_daily_volume, calculate_daily_count,
    calculate_overall_volume, calculate_overall_count, get_metrics_summary 
)
from lambda_utils.type_util.file_status import (
    DailyMetricItem, OverallMetricResult, MetricsQueryParameters
)

logger = logging.getLogger(__name__)

# --- Router Definition ---
router = APIRouter(prefix="/file_status", tags=["file_status"])

# Note: Removed the separate get_user_ngroup_id helper function from here

# --- Define Specific Paths FIRST ---

@router.get("/metrics/summary", response_model=FileStatusMetricsSummary, tags=["file_status_metrics"])
async def metrics_summary_endpoint(
    ngroup_id: UUID = Query(..., description="Mandatory NGROUP ID (DAAC/Org)"),
    params: MetricsQueryParameters = Depends(),
    current_user: dict = Depends(get_current_user_with_ngroup) # Use your auth dependency
):
    """
    Get a combined summary of file status metrics (counts, volumes)
    for a specific NGROUP, filtered. Inclusive end date. Auth required.
    """
    user_ngroup_id = current_user.get('ngroup_id') # Safely get ngroup_id
    if not user_ngroup_id:
         raise HTTPException(status_code=403, detail="User NGROUP information missing.")
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized for specified ngroup.")

    try:
        summary_data = await get_metrics_summary(ngroup_id, params)
        return summary_data
    except Exception as e:
        logger.error(f"Failed in metrics_summary_endpoint for ngroup {ngroup_id}: {e}", exc_info=True)
        # Consider more specific error handling if needed (e.g., 404 if ngroup doesn't exist)
        raise HTTPException(status_code=500, detail="Error calculating metrics summary.")


@router.get("/metrics/daily_volume", response_model=List[DailyMetricItem], tags=["file_status_metrics"])
async def daily_volume_endpoint(
    ngroup_id: UUID = Query(..., description="Mandatory NGROUP ID (DAAC/Org)"),
    params: MetricsQueryParameters = Depends(),
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    Get daily volume (GB) for a specific NGROUP, filtered. Inclusive end date. Auth required.
    """
    user_ngroup_id = current_user['ngroup_id'] # Get from enhanced dependency
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized for specified ngroup.")
    try:
        return await calculate_daily_volume(ngroup_id, params)
    except Exception as e:
        logger.error(f"Failed in daily_volume_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error calculating daily volume.")

@router.get("/metrics/daily_count", response_model=List[DailyMetricItem], tags=["file_status_metrics"])
async def daily_count_endpoint(
    ngroup_id: UUID = Query(..., description="Mandatory NGROUP ID (DAAC/Org)"),
    params: MetricsQueryParameters = Depends(),
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    Get daily count for a specific NGROUP, filtered. Inclusive end date. Auth required.
    """
    user_ngroup_id = current_user['ngroup_id']
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized for specified ngroup.")
    try:
        return await calculate_daily_count(ngroup_id, params)
    except Exception as e:
        logger.error(f"Failed in daily_count_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error calculating daily count.")

@router.get("/metrics/overall_volume", response_model=OverallMetricResult, tags=["file_status_metrics"])
async def overall_volume_endpoint(
    ngroup_id: UUID = Query(..., description="Mandatory NGROUP ID (DAAC/Org)"),
    params: MetricsQueryParameters = Depends(),
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    Get overall volume (GB) for a specific NGROUP, filtered. Inclusive end date. Auth required.
    """
    user_ngroup_id = current_user['ngroup_id']
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized for specified ngroup.")
    try:
        return await calculate_overall_volume(ngroup_id, params)
    except Exception as e:
        logger.error(f"Failed in overall_volume_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error calculating overall volume.")

@router.get("/metrics/overall_count", response_model=OverallMetricResult, tags=["file_status_metrics"])
async def overall_count_endpoint(
    ngroup_id: UUID = Query(..., description="Mandatory NGROUP ID (DAAC/Org)"),
    params: MetricsQueryParameters = Depends(),
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    Get overall count for a specific NGROUP, filtered. Inclusive end date. Auth required.
    """
    user_ngroup_id = current_user['ngroup_id']
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized for specified ngroup.")
    try:
        return await calculate_overall_count(ngroup_id, params)
    except Exception as e:
        logger.error(f"Failed in overall_count_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error calculating overall count.")

@router.get("/metrics/status_counts", response_model=Dict[str, int], tags=["file_status_metrics"])
async def status_counts_endpoint(
    ngroup_id: UUID = Query(..., description="Mandatory NGROUP ID (DAAC/Org)"),
    params: MetricsQueryParameters = Depends(),
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    Get status counts for a specific NGROUP, filtered. Inclusive end date. Auth required.
    """
    user_ngroup_id = current_user['ngroup_id']
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized for specified ngroup.")
    try:
        return await get_file_status_counts(ngroup_id, params)
    except Exception as e:
        logger.error(f"Failed in status_counts_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error calculating status counts.")

@router.get("/list_by_status", response_model=PaginatedFileResponse, tags=["file_status"])
async def list_files_by_status_endpoint(
    ngroup_id: UUID = Query(..., description="Mandatory NGROUP ID (DAAC/Org)"),
    status: str = Query(..., description="Filter files by this status (e.g., 'infected', 'clean')."),
    page: int = Query(1, ge=1, description="Page number starting from 1."),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page."),
    filters: MetricsQueryParameters = Depends(),
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    List files for a specific NGROUP by status, filtered. Inclusive end date. Auth required.
    """
    user_ngroup_id = current_user['ngroup_id']
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized for specified ngroup.")
    try:
        items, total = await list_files_by_status(ngroup_id, status, filters, page, page_size)
        return PaginatedFileResponse(items=items, total=total, page=page, page_size=page_size)
    except ValueError as e:
         raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed in list_files_by_status_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error listing files by status.")

@router.get("/", response_model=List[FileStatusReturn])
async def list_file_statuses_endpoint(
    ngroup_id: UUID = Query(..., description="Mandatory NGROUP ID"),
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    Retrieves file status records for a specific NGROUP. Auth required.
    """
    user_ngroup_id = current_user['ngroup_id']
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized for specified ngroup.")
    try:
        return await list_file_statuses(ngroup_id)
    except ValueError as e:
        logger.error(f"Failed in list_file_statuses_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in list_file_statuses_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error listing file statuses.")

# --- Define paths with parameters LAST ---

@router.post("/", response_model=FileStatusReturn)
async def create_file_status_endpoint(
    file_status: FileStatusCreate,
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    Creates a file status record. Auth required. Verifies file belongs to user's ngroup.
    """
    user_ngroup_id = current_user['ngroup_id']
    try:
        # Util function now handles the ngroup check using the passed user_ngroup_id
        return await create_file_status(file_status, user_ngroup_id)
    except AuthorizationError as e:
         raise HTTPException(status_code=403, detail=str(e))
    except (FileStatusNotFoundError, BaseFileNotFoundError) as e:
         raise HTTPException(status_code=404, detail=f"Cannot create status: {e}")
    except ValueError as e:
        logger.error(f"Failed in create_file_status_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in create_file_status_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error creating file status.")

@router.get("/{id}", response_model=FileStatusReturn)
async def get_file_status_endpoint(
    id: UUID, # This is file_id
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    Retrieves a specific file status by file ID. Auth required. Verifies file belongs to user's ngroup.
    """
    user_ngroup_id = current_user['ngroup_id']
    try:
        resource_ngroup_id = await get_ngroup_id_for_file(id)
        if resource_ngroup_id is None:
             # If file itself not found, status definitely not found
             raise FileStatusNotFoundError(id=id)
        if resource_ngroup_id != user_ngroup_id:
             raise HTTPException(status_code=403, detail="Not authorized to access this file status.")

        # Now safe to get status
        file_status = await get_file_status(id)
        return file_status
    except FileStatusNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as http_exc:
         raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in get_file_status_endpoint for id {id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error getting file status.")

@router.patch("/{id}", response_model=FileStatusReturn)
async def update_file_status_endpoint(
    id: UUID, # This is file_id
    file_status_update: FileStatusUpdate,
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    Updates a file status. Auth required. Verifies file belongs to user's ngroup.
    """
    user_ngroup_id = current_user['ngroup_id']
    try:
        resource_ngroup_id = await get_ngroup_id_for_file(id)
        if resource_ngroup_id is None:
             raise FileStatusNotFoundError(id=id)
        if resource_ngroup_id != user_ngroup_id:
             raise HTTPException(status_code=403, detail="Not authorized to update this file status.")

        updated_file_status = await update_file_status(id, file_status_update)
        return updated_file_status
    except FileStatusNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"Failed in update_file_status_endpoint for id {id}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as http_exc:
         raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in update_file_status_endpoint for id {id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error updating file status.")


@router.delete("/{id}", response_model=bool)
async def delete_file_status_endpoint(
    id: UUID, # This is file_id
    current_user: dict = Depends(get_current_user_with_ngroup) # Use new dependency
):
    """
    Deletes a file status. Auth required. Verifies file belongs to user's ngroup.
    """
    user_ngroup_id = current_user['ngroup_id']
    try:
        resource_ngroup_id = await get_ngroup_id_for_file(id)
        if resource_ngroup_id is None:
             raise FileStatusNotFoundError(id=id)
        if resource_ngroup_id != user_ngroup_id:
             raise HTTPException(status_code=403, detail="Not authorized to delete this file status.")

        success = await delete_file_status(id)
        return success
    except FileStatusNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as http_exc:
         raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in delete_file_status_endpoint for id {id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error deleting file status.")