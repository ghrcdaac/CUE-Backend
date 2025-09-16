# File: src/python/api/v2/utils/file_metrics.py

from uuid import UUID
from typing import Dict, Any, List, Tuple
from fastapi import Request
import structlog

from v2.database_util import file_metrics as metrics_db
from v2.type_util.file_metrics import MetricsQueryParameters

logger = structlog.get_logger(__name__)
BYTES_TO_GB = 1 / (1024**3)

async def get_daily_volume(request: Request, ngroup_id: UUID, filters: MetricsQueryParameters) -> List[Dict[str, Any]]:
    filter_dict = filters.model_dump(exclude_unset=True)
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_daily_volume(conn, ngroup_id, filter_dict)
    # ---  Convert Decimal to float before multiplying ---
    return [{"day": row['day'].date(), "value": float(row['value'] or 0) * BYTES_TO_GB} for row in data]

async def get_daily_count(request: Request, ngroup_id: UUID, filters: MetricsQueryParameters) -> List[Dict[str, Any]]:
    filter_dict = filters.model_dump(exclude_unset=True)
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_daily_count(conn, ngroup_id, filter_dict)
    return [{"day": row['day'].date(), "value": int(row['value'] or 0)} for row in data]

async def get_overall_volume(request: Request, ngroup_id: UUID, filters: MetricsQueryParameters) -> Dict[str, Any]:
    filter_dict = filters.model_dump(exclude_unset=True)
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_overall_volume(conn, ngroup_id, filter_dict)
    # ---  Convert Decimal to float before multiplying ---
    return {"value": float(data or 0) * BYTES_TO_GB}

async def get_overall_count(request: Request, ngroup_id: UUID, filters: MetricsQueryParameters) -> Dict[str, Any]:
    filter_dict = filters.model_dump(exclude_unset=True)
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_overall_count(conn, ngroup_id, filter_dict)
    return {"value": int(data or 0)}

async def get_status_counts(request: Request, ngroup_id: UUID, filters: MetricsQueryParameters) -> List[Dict[str, Any]]:
    filter_dict = filters.model_dump(exclude_unset=True)
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_status_counts(conn, ngroup_id, filter_dict)
    return [{"status": row['status'], "count": int(row['count'] or 0)} for row in data]

async def get_metrics_summary(request: Request, ngroup_id: UUID, filters: MetricsQueryParameters) -> Dict[str, Any]:
    """Calculates and aggregates all file metrics."""
    # This function now correctly calls the fixed helpers above
    daily_volume = await get_daily_volume(request, ngroup_id, filters)
    daily_count = await get_daily_count(request, ngroup_id, filters)
    overall_volume = await get_overall_volume(request, ngroup_id, filters)
    overall_count = await get_overall_count(request, ngroup_id, filters)
    status_counts = await get_status_counts(request, ngroup_id, filters)
    return {
        "daily_volume": daily_volume,
        "daily_count": daily_count,
        "overall_volume": overall_volume,
        "overall_count": overall_count,
        "status_counts": status_counts,
    }

async def get_cost_summary(request: Request, ngroup_id: UUID, filters: MetricsQueryParameters) -> Dict[str, Any]:
    filter_dict = filters.model_dump(exclude_unset=True)
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_cost_summary_data(conn, ngroup_id, filter_dict)
    return {
        "daily_cost": [{"day": row['day'].date(), "value": float(row['value'] or 0)} for row in data['daily_cost']],
        "total_cost": {"value": float(data['total_cost'] or 0)},
        "total_files": int(data['total_files'] or 0),
        # ---  Convert Decimal to float before multiplying ---
        "total_size_gb": float(data['total_size_bytes'] or 0) * BYTES_TO_GB
    }

async def get_cost_by_collection(
    request: Request, ngroup_id: UUID, filters: MetricsQueryParameters, page: int, page_size: int
) -> Tuple[List[Dict[str, Any]], int]:
    filter_dict = filters.model_dump(exclude_unset=True)
    offset = (page - 1) * page_size
    async with request.state.pool.acquire() as conn:
        total = await metrics_db.count_cost_by_collection(conn, ngroup_id, filter_dict)
        items = await metrics_db.get_cost_by_collection(conn, ngroup_id, filter_dict, page_size, offset)
    
    formatted_items = [{
        "name": item['name'],
        # ---  Convert Decimal to float before multiplying ---
        "size_gb": float(item['size_bytes'] or 0) * BYTES_TO_GB,
        "cost": float(item['cost'] or 0)
    } for item in items]
    return formatted_items, total

async def get_cost_by_file(
    request: Request, ngroup_id: UUID, filters: MetricsQueryParameters, page: int, page_size: int
) -> Tuple[List[Dict[str, Any]], int]:
    filter_dict = filters.model_dump(exclude_unset=True)
    offset = (page - 1) * page_size
    async with request.state.pool.acquire() as conn:
        total = await metrics_db.count_cost_by_file(conn, ngroup_id, filter_dict)
        items = await metrics_db.get_cost_by_file(conn, ngroup_id, filter_dict, page_size, offset)

    formatted_items = [{
        "name": item['name'],
        # ---  Convert Decimal to float before multiplying ---
        "size_gb": float(item['size_bytes'] or 0) * BYTES_TO_GB,
        "cost": float(item['cost'] or 0)
    } for item in items]
    return formatted_items, total