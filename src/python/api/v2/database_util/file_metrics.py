# File: src/python/api/v2/database_util/file_metrics.py

from asyncpg import Connection
from typing import List, Dict, Any, Tuple
from uuid import UUID

def _build_metrics_query_parts(
    ngroup_id: UUID, filters: Dict[str, Any], mandatory_conditions: Dict[str, Any] = None
) -> Tuple[str, List[Any]]:
    """Helper to build WHERE clauses and parameters for metric queries."""
    where_clauses = ["c.ngroup_id = $1"]
    params = [ngroup_id]
    
    filter_map = {
        "start_date": "fs.upload_time >= ${index}",
        "end_date": "fs.upload_time < (${index}::date + interval '1 day')",
        "user_id": "f.cueuser_uploaded = ${index}",
        "collection_id": "f.collection_id = ${index}",
        "provider_id": "c.provider_id = ${index}"
    }

    if mandatory_conditions:
        for key, value in mandatory_conditions.items():
            params.append(value)
            where_clauses.append(f"{key} = ${len(params)}")

    for key, value in filters.items():
        if key in filter_map:
            params.append(value)
            where_clauses.append(filter_map[key].format(index=len(params)))

    from_clause = """
        FROM file f
        JOIN file_status fs ON f.id = fs.id
        JOIN collection c ON f.collection_id = c.id
    """
    where_clause = "WHERE " + " AND ".join(where_clauses)
    
    return f"{from_clause} {where_clause}", params

async def get_metrics_summary_data(conn: Connection, ngroup_id: UUID, filters: Dict[str, Any]) -> Dict[str, Any]:
    query_suffix, params = _build_metrics_query_parts(ngroup_id, filters)
    # Queries remain largely the same, but are now consolidated here
    daily_volume_q = f"SELECT DATE_TRUNC('day', fs.upload_time) AS day, SUM(f.size_bytes) AS value {query_suffix} GROUP BY day ORDER BY day;"
    daily_count_q = f"SELECT DATE_TRUNC('day', fs.upload_time) AS day, COUNT(f.id) AS value {query_suffix} GROUP BY day ORDER BY day;"
    overall_volume_q = f"SELECT SUM(f.size_bytes) AS value {query_suffix};"
    overall_count_q = f"SELECT COUNT(f.id) AS value {query_suffix};"
    status_counts_q = f"SELECT fs.status, COUNT(f.id) AS count {query_suffix} GROUP BY fs.status;"

    return {
        "daily_volume": await conn.fetch(daily_volume_q, *params),
        "daily_count": await conn.fetch(daily_count_q, *params),
        "overall_volume": await conn.fetchval(overall_volume_q, *params),
        "overall_count": await conn.fetchval(overall_count_q, *params),
        "status_counts": await conn.fetch(status_counts_q, *params)
    }

async def list_files_by_status(conn: Connection, ngroup_id: UUID, status: str, filters: Dict[str, Any], limit: int, offset: int) -> List[Dict[str, Any]]:
    mandatory = {'fs.status': status}
    query_suffix, params = _build_metrics_query_parts(ngroup_id, filters, mandatory_conditions=mandatory)
    
    select_clause = """
        SELECT f.*, fs.status, fs.upload_time, fs.scan_start, fs.scan_end, fs.egress_start, fs.scan_results
    """
    pagination_clause = f" ORDER BY fs.upload_time DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
    params.extend([limit, offset])
    
    return await conn.fetch(select_clause + query_suffix + pagination_clause, *params)

async def count_files_by_status(conn: Connection, ngroup_id: UUID, status: str, filters: Dict[str, Any]) -> int:
    mandatory = {'fs.status': status}
    query_suffix, params = _build_metrics_query_parts(ngroup_id, filters, mandatory_conditions=mandatory)
    count = await conn.fetchval(f"SELECT COUNT(f.id) {query_suffix}", *params)
    return count or 0

async def get_cost_by_collection(conn: Connection, ngroup_id: UUID, filters: Dict[str, Any], limit: int, offset: int) -> List[Dict[str, Any]]:
    query_suffix, params = _build_metrics_query_parts(ngroup_id, filters)
    select_clause = """
        SELECT c.short_name as name, SUM(f.size_bytes) as size_bytes,
               SUM(cm.scanner_cost + cm.aws_transfer_cost) as cost
    """
    join_clause = " JOIN cost_metric cm ON f.id = cm.file_id "
    pagination_clause = f" GROUP BY c.short_name ORDER BY cost DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
    params.extend([limit, offset])

    return await conn.fetch(select_clause + query_suffix + join_clause + pagination_clause, *params)