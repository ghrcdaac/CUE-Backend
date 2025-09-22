from asyncpg import Connection
from typing import List, Dict, Any, Tuple, Optional
from uuid import UUID

def _build_metrics_query_parts(
    requesting_user: Dict[str, Any],
    active_ngroup_id: Optional[UUID],
    filters: Dict[str, Any]
) -> Tuple[str, str, List[Any]]:
    """
    Helper to build the main FROM and WHERE clauses for metric queries.
    """
    user_roles = set(requesting_user.get('roles', []))
    params = []
    where_clauses = []

    if active_ngroup_id:
        params.append(active_ngroup_id)
        where_clauses.append(f"c.ngroup_id = ${len(params)}")
    else:
        if 'admin' not in user_roles and 'security' not in user_roles:
            where_clauses.append("FALSE")
    
    filter_map = {
        "start_date": "fs.upload_time >= ${index}::date",
        "end_date": "fs.upload_time < (${index}::date + interval '1 day')",
        "user_id": "f.cueuser_uploaded = ${index}",
        "collection_id": "f.collection_id = ${index}",
        "provider_id": "c.provider_id = ${index}"
    }

    for key, value in filters.items():
        if key in filter_map and value is not None:
            params.append(value)
            where_clauses.append(filter_map[key].format(index=len(params)))

    from_clause = """
        FROM file f
        JOIN file_status fs ON f.id = fs.id
        JOIN collection c ON f.collection_id = c.id
    """
    where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    return from_clause, where_clause, params

# --- Standard V2 Metrics (no cost calculation) ---
async def get_daily_volume(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    from_clause, where_clause, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    query = f"SELECT DATE_TRUNC('day', fs.upload_time) AS day, SUM(f.size_bytes) AS value {from_clause} {where_clause} GROUP BY day ORDER BY day;"
    return await conn.fetch(query, *params)

async def get_daily_count(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    from_clause, where_clause, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    query = f"SELECT DATE_TRUNC('day', fs.upload_time) AS day, COUNT(f.id) AS value {from_clause} {where_clause} GROUP BY day ORDER BY day;"
    return await conn.fetch(query, *params)

async def get_overall_volume(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> int:
    from_clause, where_clause, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    query = f"SELECT SUM(f.size_bytes) AS value {from_clause} {where_clause};"
    return await conn.fetchval(query, *params) or 0

async def get_overall_count(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> int:
    from_clause, where_clause, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    query = f"SELECT COUNT(f.id) AS value {from_clause} {where_clause};"
    return await conn.fetchval(query, *params) or 0

async def get_status_counts(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    from_clause, where_clause, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    query = f"SELECT fs.status, COUNT(f.id) AS count {from_clause} {where_clause} GROUP BY fs.status;"
    return await conn.fetch(query, *params)

# --- V1-style Database Functions for Cost Calculation ---
async def get_daily_metrics_for_cost_calc(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    from_clause, where_clause, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    select_clause = "SELECT DATE(fs.upload_time) as date, SUM(f.size_bytes) as size, SUM(EXTRACT(EPOCH FROM (scan_end - scan_start))) as scan_duration, count(f.id) as file_count"
    groupby_clause = " GROUP BY DATE(fs.upload_time)"
    full_query = select_clause + from_clause + where_clause + groupby_clause
    return await conn.fetch(full_query, *params)

async def get_collection_metrics_for_cost_calc(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any], limit: int, offset: int) -> List[Dict[str, Any]]:
    from_clause, where_clause, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    select_clause = "SELECT c.short_name as name, SUM(f.size_bytes) as size, SUM(EXTRACT(EPOCH FROM (fs.scan_end - fs.scan_start))) as scan_duration "
    groupby_clause = " GROUP BY f.collection_id, c.short_name ORDER BY c.short_name"
    pagination_clause = f" LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
    params.extend([limit, offset])
    full_query = select_clause + from_clause + where_clause + groupby_clause + pagination_clause
    return await conn.fetch(full_query, *params)

async def count_collection_metrics(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> int:
    from_clause, where_clause, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    count = await conn.fetchval(f"SELECT COUNT(DISTINCT(c.id)) {from_clause} {where_clause}", *params)
    return int(count) if count is not None else 0

async def get_file_metrics_for_cost_calc(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any], limit: int, offset: int) -> List[Dict[str, Any]]:
    from_clause, where_clause, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    select_clause = "SELECT f.name as name, f.size_bytes as size, EXTRACT(EPOCH FROM (fs.scan_end - fs.scan_start)) as scan_duration "
    orderby_clause = " ORDER BY size DESC NULLS LAST"
    pagination_clause = f" LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
    params.extend([limit, offset])
    full_query = select_clause + from_clause + where_clause + orderby_clause + pagination_clause
    return await conn.fetch(full_query, *params)

async def count_file_metrics(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> int:
    from_clause, where_clause, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    count = await conn.fetchval(f"SELECT COUNT(f.id) {from_clause} {where_clause}", *params)
    return int(count) if count is not None else 0