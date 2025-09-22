from uuid import UUID
from typing import Dict, Any, List, Tuple, Optional
from fastapi import Request
import structlog

from v2.type_util.auth import AuthUser
from v2.database_util import file_metrics as metrics_db
from v2.type_util.file_metrics import MetricsQueryParameters

logger = structlog.get_logger(__name__)
BYTES_TO_GB = 1 / (1024**3)

# --- ALL utility functions now accept 'user' and 'active_ngroup_id' ---

async def get_daily_volume(
    request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters
) -> List[Dict[str, Any]]:
    filter_dict = filters.model_dump(exclude_unset=True)
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_daily_volume(conn, user.model_dump(), ngroup_id_to_filter, filter_dict)
    return [{"day": row['day'].date(), "value": float(row['value'] or 0) * BYTES_TO_GB} for row in data]

async def get_daily_count(
    request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters
) -> List[Dict[str, Any]]:
    filter_dict = filters.model_dump(exclude_unset=True)
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_daily_count(conn, user.model_dump(), ngroup_id_to_filter, filter_dict)
    return [{"day": row['day'].date(), "value": int(row['value'] or 0)} for row in data]

async def get_overall_volume(
    request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters
) -> Dict[str, Any]:
    filter_dict = filters.model_dump(exclude_unset=True)
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_overall_volume(conn, user.model_dump(), ngroup_id_to_filter, filter_dict)
    return {"value": float(data or 0) * BYTES_TO_GB}

async def get_overall_count(
    request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters
) -> Dict[str, Any]:
    filter_dict = filters.model_dump(exclude_unset=True)
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_overall_count(conn, user.model_dump(), ngroup_id_to_filter, filter_dict)
    return {"value": int(data or 0)}

async def get_status_counts(
    request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters
) -> List[Dict[str, Any]]:
    filter_dict = filters.model_dump(exclude_unset=True)
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_status_counts(conn, user.model_dump(), ngroup_id_to_filter, filter_dict)
    return [{"status": row['status'], "count": int(row['count'] or 0)} for row in data]

async def get_metrics_summary(
    request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters
) -> Dict[str, Any]:
    """Calculates and aggregates all file metrics for the selected group."""
    daily_volume = await get_daily_volume(request, user, active_ngroup_id, filters)
    daily_count = await get_daily_count(request, user, active_ngroup_id, filters)
    overall_volume = await get_overall_volume(request, user, active_ngroup_id, filters)
    overall_count = await get_overall_count(request, user, active_ngroup_id, filters)
    status_counts = await get_status_counts(request, user, active_ngroup_id, filters)
    return {
        "daily_volume": daily_volume, "daily_count": daily_count,
        "overall_volume": overall_volume, "overall_count": overall_count,
        "status_counts": status_counts,
    }

async def get_cost_summary(
    request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters
) -> Dict[str, Any]:
    filter_dict = filters.model_dump(exclude_unset=True)
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_cost_summary_data(conn, user.model_dump(), ngroup_id_to_filter, filter_dict)
    return {
        "daily_cost": [{"day": row['day'].date(), "value": float(row['value'] or 0)} for row in data['daily_cost']],
        "total_cost": {"value": float(data['total_cost'] or 0)},
        "total_files": int(data['total_files'] or 0),
        "total_size_gb": float(data['total_size_bytes'] or 0) * BYTES_TO_GB
    }

async def get_cost_by_collection(
    request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters, page: int, page_size: int
) -> Tuple[List[Dict[str, Any]], int]:
    filter_dict = filters.model_dump(exclude_unset=True)
    offset = (page - 1) * page_size
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    user_dump = user.model_dump()
    async with request.state.pool.acquire() as conn:
        total = await metrics_db.count_cost_by_collection(conn, user_dump, ngroup_id_to_filter, filter_dict)
        items = await metrics_db.get_cost_by_collection(conn, user_dump, ngroup_id_to_filter, filter_dict, page_size, offset)
    
    formatted_items = [{
        "name": item['name'], "size_gb": float(item['size_bytes'] or 0) * BYTES_TO_GB, "cost": float(item['cost'] or 0)
    } for item in items]
    return formatted_items, total

async def get_cost_by_file(
    request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters, page: int, page_size: int
) -> Tuple[List[Dict[str, Any]], int]:
    filter_dict = filters.model_dump(exclude_unset=True)
    offset = (page - 1) * page_size
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    user_dump = user.model_dump()
    async with request.state.pool.acquire() as conn:
        total = await metrics_db.count_cost_by_file(conn, user_dump, ngroup_id_to_filter, filter_dict)
        items = await metrics_db.get_cost_by_file(conn, user_dump, ngroup_id_to_filter, filter_dict, page_size, offset)

    formatted_items = [{
        "name": item['name'], "size_gb": float(item['size_bytes'] or 0) * BYTES_TO_GB, "cost": float(item['cost'] or 0)
    } for item in items]
    return formatted_items, total
