from fastapi import APIRouter, Query
from utils.file_metrics import get_sample_summary_cost, get_sample_collection_cost, get_sample_file_cost
from lambda_utils.type_util.file_metrics import SummaryCostReturn, CostReturn
from uuid import UUID
from typing import Optional, List
from datetime import datetime
import logging

router = APIRouter(prefix="/file_metrics", tags=["file_metrics"])
logger = logging.getLogger(__name__)

@router.get("/cost_summary", response_model=SummaryCostReturn)
async def get_cost_summary(
    ngroup_id: UUID = Query(..., description="ngroup ID"),
    start_date: Optional[datetime] = Query(None, description="start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="end date for filtering"),
    collection_id: Optional[UUID] = Query(None, description="collection ID for filtering"),
    provider_id: Optional[UUID] = Query(None, description="provider ID for filtering"),
    user_id: Optional[UUID] = Query(None, description="user ID for filtering"),
):
    return await get_sample_summary_cost()

@router.get("/collection_cost", response_model=List[CostReturn])
async def get_collection_cost(
    ngroup_id: UUID = Query(..., description="ngroup ID"), 
    start_date: Optional[datetime] = Query(None, description="start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="end date for filtering"),
    collection_id: Optional[UUID] = Query(None, description="collection ID for filtering"),
    provider_id: Optional[UUID] = Query(None, description="provider ID for filtering"),
    user_id: Optional[UUID] = Query(None, description="user ID for filtering"),
    page: int = Query(1, description="Page number, starting from 1"),
    page_size: int = Query(10, description="Number of items per page")
):
    return await get_sample_collection_cost()

@router.get("/file_cost", response_model=List[CostReturn])
async def get_file_cost(
    ngroup_id: UUID = Query(..., description="ngroup ID" ), 
    start_date: Optional[datetime] = Query(None, description="start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="end date for filtering"),
    collection_id: Optional[UUID] = Query(None, description="collection ID for filtering"),
    provider_id: Optional[UUID] = Query(None, description="provider ID for filtering"),
    user_id: Optional[UUID] = Query(None, description="user ID for filtering"),
    page: int = Query(1, description="Page number, starting from 1"),
    page_size: int = Query(10, description="Number of items per page")
):
    return await get_sample_file_cost()
