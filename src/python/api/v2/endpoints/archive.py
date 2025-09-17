# File: src/python/api/v2/endpoints/archive.py

from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
import structlog

from core.security import get_current_user, require_privilege
from v2.type_util.auth import AuthUser
from v2.utils import archive as archive_utils
from v2.type_util.archive import (
    ArchiveQueryRequest, ArchiveQueryStartResponse,
    ArchiveQueryStatusResponse, ArchiveQueryResultsResponse
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/archive", tags=["V2 - Archive"])

@router.post("/queries", response_model=ArchiveQueryStartResponse,
             status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_privilege("archive:query"))])
async def start_archive_query_endpoint(
    request: ArchiveQueryRequest,
    user: AuthUser = Depends(get_current_user)
):
    """
    Starts an asynchronous query of the historical data archive for the user's active ngroup.
    Returns a query execution ID to be used for checking status and retrieving results.
    """
    if not user.active_ngroup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active ngroup header is required.")
    
    ngroup_id = UUID(user.active_ngroup_id)
    try:
        query_id = await archive_utils.start_archive_query(ngroup_id, request)
        return ArchiveQueryStartResponse(query_execution_id=query_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (archive_utils.AthenaError, Exception) as e:
        logger.error("endpoint.start_archive_query.failed", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/queries/{query_execution_id}/status", response_model=ArchiveQueryStatusResponse,
            dependencies=[Depends(require_privilege("archive:query"))])
async def get_query_status_endpoint(query_execution_id: str, _user: AuthUser = Depends(get_current_user)):
    """Checks the status of a running archive query."""
    try:
        status_info = await archive_utils.get_query_status(query_execution_id)
        return ArchiveQueryStatusResponse(**status_info)
    except (archive_utils.AthenaError, Exception) as e:
        logger.error("endpoint.get_query_status.failed", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/queries/{query_execution_id}/results", response_model=ArchiveQueryResultsResponse,
            dependencies=[Depends(require_privilege("archive:query"))])
async def get_query_results_endpoint(query_execution_id: str, _user: AuthUser = Depends(get_current_user)):
    """
    Retrieves the results of a completed archive query.
    Note: Access control to ensure the user owns this query is not yet implemented.
    """
    try:
        results = await archive_utils.get_query_results(query_execution_id)
        return ArchiveQueryResultsResponse(items=results)
    except (archive_utils.AthenaError, Exception) as e:
        logger.error("endpoint.get_query_results.failed", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))