# File: src/python/api/v2/utils/file_metrics.py

from uuid import UUID
from typing import Dict, Any, List, Tuple, Optional
from fastapi import Request
import structlog
from decimal import Decimal, getcontext
from math import ceil

from v2.type_util.auth import AuthUser
from v2.database_util import file_metrics as metrics_db
from v2.type_util.file_metrics import MetricsQueryParameters

logger = structlog.get_logger(__name__)

getcontext().rounding = "ROUND_UP"

# Constants for V1-style cost calculation
AWS_COST_PER_BYTE = Decimal("0.00000000001") 
SCAN_COST_PER_SECOND = Decimal("0.00005")      


# --- Standard V2 Metrics (no cost calculation) ---
async def get_daily_volume(request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters) -> List[Dict[str, Any]]:
    filter_dict = filters.model_dump(exclude_unset=True)
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_daily_volume(conn, user.model_dump(), ngroup_id_to_filter, filter_dict)
    return [{"day": row['day'].date(), "value": int(row['value'] or 0)} for row in data]

async def get_daily_count(request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters) -> List[Dict[str, Any]]:
    filter_dict = filters.model_dump(exclude_unset=True)
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_daily_count(conn, user.model_dump(), ngroup_id_to_filter, filter_dict)
    return [{"day": row['day'].date(), "value": int(row['value'] or 0)} for row in data]

async def get_overall_volume(request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters) -> Dict[str, Any]:
    filter_dict = filters.model_dump(exclude_unset=True)
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_overall_volume(conn, user.model_dump(), ngroup_id_to_filter, filter_dict)
    return {"value": int(data or 0)}


async def get_overall_count(request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters) -> Dict[str, Any]:
    filter_dict = filters.model_dump(exclude_unset=True)
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_overall_count(conn, user.model_dump(), ngroup_id_to_filter, filter_dict)
    return {"value": int(data or 0)}

async def get_status_counts(request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters) -> List[Dict[str, Any]]:
    filter_dict = filters.model_dump(exclude_unset=True)
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_status_counts(conn, user.model_dump(), ngroup_id_to_filter, filter_dict)
    return [{"status": row['status'], "count": int(row['count'] or 0)} for row in data]

async def get_metrics_summary(request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters) -> Dict[str, Any]:
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


# --- V1-style Cost Calculation Logic ---
async def get_summary_cost(request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters) -> Dict[str, Any]:
    filter_dict = filters.model_dump(exclude_unset=True)
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    user_dump = user.model_dump()
    
    async with request.state.pool.acquire() as conn:
        daily_metrics = await metrics_db.get_daily_metrics_for_cost_calc(conn, user_dump, ngroup_id_to_filter, filter_dict)

    daily_cost, total_cost_val, total_files, total_size_bytes = [], Decimal(0), 0, 0
    for record in daily_metrics:
        size = Decimal(record.get("size", 0))
        scan_duration = Decimal(record.get('scan_duration', 0)) if record.get('scan_duration') else Decimal(0)
        cost = (size * AWS_COST_PER_BYTE) + (scan_duration * SCAN_COST_PER_SECOND)
        daily_cost.append({"day": record["date"], "value": float(cost.quantize(Decimal("0.01")))})
        total_cost_val += cost
        total_files += record.get("file_count", 0)
        total_size_bytes += int(size) 

    return {
        "daily_cost": daily_cost,
        "total_cost": {"value": float(total_cost_val.quantize(Decimal("0.01")))},
        "total_files": total_files,
        "total_size_bytes": total_size_bytes
    }

async def get_cost_by_collection(request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters, page: int, page_size: int) -> Tuple[List[Dict[str, Any]], int]:
    filter_dict = filters.model_dump(exclude_unset=True)
    offset = (page - 1) * page_size
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    user_dump = user.model_dump()
    
    async with request.state.pool.acquire() as conn:
        total = await metrics_db.count_collection_metrics(conn, user_dump, ngroup_id_to_filter, filter_dict)
        items = await metrics_db.get_collection_metrics_for_cost_calc(conn, user_dump, ngroup_id_to_filter, filter_dict, page_size, offset)

    collection_cost = []
    for record in items:
        size = Decimal(record.get('size', 0))
        scan_duration = Decimal(record.get('scan_duration', 0)) if record.get('scan_duration') else Decimal(0)
        cost = (size * AWS_COST_PER_BYTE) + (scan_duration * SCAN_COST_PER_SECOND)
        collection_cost.append({
            "name": record.get("name"),
            "size_bytes": int(size),
            "cost": float(cost.quantize(Decimal("0.01")))
        })
    return collection_cost, total

async def get_cost_by_file(request: Request, user: AuthUser, active_ngroup_id: Optional[str], filters: MetricsQueryParameters, page: int, page_size: int) -> Tuple[List[Dict[str, Any]], int]:
    filter_dict = filters.model_dump(exclude_unset=True)
    offset = (page - 1) * page_size
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    user_dump = user.model_dump()

    async with request.state.pool.acquire() as conn:
        total = await metrics_db.count_file_metrics(conn, user_dump, ngroup_id_to_filter, filter_dict)
        items = await metrics_db.get_file_metrics_for_cost_calc(conn, user_dump, ngroup_id_to_filter, filter_dict, page_size, offset)

    file_cost = []
    for record in items:
        size = Decimal(record.get('size', 0))
        scan_duration = Decimal(record.get('scan_duration', 0)) if record.get('scan_duration') else Decimal(0)
        cost = (size * AWS_COST_PER_BYTE) + (scan_duration * SCAN_COST_PER_SECOND)
        file_cost.append({
            "name": record.get("name"),
            "size_bytes": int(size),
            "cost": float(cost.quantize(Decimal("0.01")))
        })
    return file_cost, total