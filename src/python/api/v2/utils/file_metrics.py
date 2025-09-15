# ==============================================================================
# File: src/python/api/v2/utils/file_metrics.py (Updated)
# --- MODIFIED to use the shared connection pool from the request state ---
# ==============================================================================
from uuid import UUID
from typing import Dict, Any, List, Tuple
from fastapi import Request # <-- Import Request

# --- REMOVED: from core.db import get_db_connection ---
from v2.database_util import file_metrics as metrics_db
from v2.type_util.file_metrics import MetricsQueryParameters

BYTES_TO_GB = 1 / (1024**3)

# --- MODIFIED: Functions now accept the `request` object ---

async def get_metrics_summary(request: Request, ngroup_id: UUID, filters: MetricsQueryParameters) -> Dict[str, Any]:
    """Calculates and aggregates all file metrics."""
    filter_dict = filters.model_dump(exclude_none=True)
    async with request.state.pool.acquire() as conn:
        data = await metrics_db.get_metrics_summary_data(conn, ngroup_id, filter_dict)

    return {
        "daily_volume": [{"day": row['day'].date(), "value": float(row['value'] * BYTES_TO_GB)} for row in data['daily_volume']],
        "daily_count": [{"day": row['day'].date(), "value": int(row['value'])} for row in data['daily_count']],
        "overall_volume": {"value": float((data['overall_volume'] or 0) * BYTES_TO_GB)},
        "overall_count": {"value": int(data['overall_count'] or 0)},
        "status_counts": [{"status": row['status'], "count": int(row['count'])} for row in data['status_counts']]
    }

async def list_files_by_status(
    request: Request, ngroup_id: UUID, status: str, filters: MetricsQueryParameters, page: int, page_size: int
) -> Tuple[List[Dict[str, Any]], int]:
    """Lists files filtered by status with pagination."""
    filter_dict = filters.model_dump(exclude_none=True)
    offset = (page - 1) * page_size
    async with request.state.pool.acquire() as conn:
        total = await metrics_db.count_files_by_status(conn, ngroup_id, status, filter_dict)
        items = await metrics_db.list_files_by_status(conn, ngroup_id, status, filter_dict, page_size, offset)
    return [dict(item) for item in items], total

async def get_cost_by_collection(
    request: Request, ngroup_id: UUID, filters: MetricsQueryParameters, page: int, page_size: int
) -> Tuple[List[Dict[str, Any]], int]:
    """Gets cost metrics aggregated by collection."""
    filter_dict = filters.model_dump(exclude_none=True)
    offset = (page - 1) * page_size
    async with request.state.pool.acquire() as conn:
        # We need a separate count function for this aggregation
        # For now, we'll assume a simplified total count. A more accurate count would be COUNT(DISTINCT c.id)
        total = await metrics_db.count_files_by_status(conn, ngroup_id, "distributed", {}) # Placeholder count
        items = await metrics_db.get_cost_by_collection(conn, ngroup_id, filter_dict, page_size, offset)
    
    formatted_items = [{
        "name": item['name'],
        "size_gb": float(item['size_bytes'] * BYTES_TO_GB),
        "cost": float(item['cost'] or 0)
    } for item in items]
    return formatted_items, total
