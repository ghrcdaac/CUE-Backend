from uuid import UUID
from typing import List, Dict
from datetime import date
from fastapi import APIRouter, HTTPException, Depends, Query
from v2.utils.auth import get_current_user_with_ngroup, get_cognito_auth # Keep old one if needed elsewhere
from v2.utils.archive import start_archive_query, get_query_status, get_query_results
from lambda_utils.type_util.file_status import MetricsQueryParameters
from lambda_utils.type_util.archive import ArchiveRequestBody, ArchiveReturn
import logging

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/archive", tags=["archive"])

@router.post("/queries", response_model=UUID)
async def start_archive_metrics_query(request_body: ArchiveRequestBody,
                                      current_user: dict = Depends(get_current_user_with_ngroup)):
    """Queries archive database for aged off metrics"""
    ngroup_id = request_body.ngroup_id
    user_ngroup_id = current_user['ngroup_id']
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized for specified ngroup.")
    try:
        query_exc_id = await start_archive_query(ngroup_id, request_body)
        return query_exc_id
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed in start_archive_metrics_query endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error starting archive query.")


@router.get("/queries/{query_execution_id}/status", response_model=str)
async def get_archive_metrics_query_status(query_execution_id:str,
                                            ngroup_id:UUID = Query(..., description="Mandatory NGROUP ID (DAAC/Org)") ,
                                            current_user: dict = Depends(get_current_user_with_ngroup)):
    """Gets the status a of archive query"""
    user_ngroup_id = current_user['ngroup_id']
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized for specified ngroup.")
    try:
        results = await get_query_status(query_execution_id)
        return results
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed in get_archive_metrics_status endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting file metrics from archive.")


@router.get("/queries/{query_execution_id}/results", response_model=List[ArchiveReturn])
async def get_archive_metrics_query_results(query_execution_id: UUID,
                                            ngroup_id: UUID = Query(..., description="Mandatory NGROUP ID (DAAC/Org)"),
                                            current_user: dict = Depends(get_current_user_with_ngroup)):
    """Gets the results of a archive query"""
    user_ngroup_id = current_user['ngroup_id']
    if ngroup_id != user_ngroup_id:
        raise HTTPException(status_code=403, detail="Not authorized for specified ngroup.")
    try:
        results = await get_query_results(query_execution_id)
        return results
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed in get_archive_metrics_query_results endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting file metrics from archive.")
