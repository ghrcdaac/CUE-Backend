from asyncpg import Connection
from typing import List, Dict, Any, Tuple, Optional
from uuid import UUID

def _build_metrics_query_parts(
    requesting_user: Dict[str, Any],
    active_ngroup_id: Optional[UUID],
    filters: Dict[str, Any]
) -> Tuple[str, List[Any]]:
    """Helper to build WHERE clauses and parameters for metric queries, respecting user roles."""
    user_roles = set(requesting_user.get('roles', []))
    params = []
    where_clauses = []

    # --- DAAC filtering logic ---
    if active_ngroup_id:
        params.append(active_ngroup_id)
        where_clauses.append(f"c.ngroup_id = ${len(params)}")
    else:
        if 'admin' not in user_roles and 'security' not in user_roles:
            # Non-admins MUST select a DAAC to see any metrics.
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
    
    return f"{from_clause} {where_clause}", params

# --- ALL database functions now accept 'requesting_user' and 'active_ngroup_id' ---

async def get_daily_volume(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    query_suffix, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    query = f"SELECT DATE_TRUNC('day', fs.upload_time) AS day, SUM(f.size_bytes) AS value {query_suffix} GROUP BY day ORDER BY day;"
    return await conn.fetch(query, *params)

async def get_daily_count(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    query_suffix, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    query = f"SELECT DATE_TRUNC('day', fs.upload_time) AS day, COUNT(f.id) AS value {query_suffix} GROUP BY day ORDER BY day;"
    return await conn.fetch(query, *params)

async def get_overall_volume(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> int:
    query_suffix, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    query = f"SELECT SUM(f.size_bytes) AS value {query_suffix};"
    return await conn.fetchval(query, *params) or 0

async def get_overall_count(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> int:
    query_suffix, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    query = f"SELECT COUNT(f.id) AS value {query_suffix};"
    return await conn.fetchval(query, *params) or 0

async def get_status_counts(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    query_suffix, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    query = f"SELECT fs.status, COUNT(f.id) AS count {query_suffix} GROUP BY fs.status;"
    return await conn.fetch(query, *params)

async def get_cost_summary_data(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> Dict[str, Any]:
    query_suffix, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    join_clause = " LEFT JOIN cost_metric cm ON f.id = cm.file_id "
    daily_cost_q = f"SELECT DATE_TRUNC('day', fs.upload_time) AS day, SUM(cm.total_cost) AS value {query_suffix}{join_clause} GROUP BY day ORDER BY day;"
    total_cost_q = f"SELECT SUM(cm.total_cost) {query_suffix}{join_clause};"
    total_files_q = f"SELECT COUNT(f.id) {query_suffix};"
    total_size_q = f"SELECT SUM(f.size_bytes) {query_suffix};"
    return {
        "daily_cost": await conn.fetch(daily_cost_q, *params),
        "total_cost": await conn.fetchval(total_cost_q, *params),
        "total_files": await conn.fetchval(total_files_q, *params),
        "total_size_bytes": await conn.fetchval(total_size_q, *params)
    }

async def get_cost_by_collection(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any], limit: int, offset: int) -> List[Dict[str, Any]]:
    query_suffix, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    join_clause = " LEFT JOIN cost_metric cm ON f.id = cm.file_id "
    select_clause = "SELECT c.short_name as name, SUM(f.size_bytes) as size_bytes, SUM(cm.total_cost) as cost "
    group_by_clause = " GROUP BY c.short_name ORDER BY cost DESC"
    pagination_clause = f" LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
    params.extend([limit, offset])
    return await conn.fetch(select_clause + query_suffix + join_clause + group_by_clause + pagination_clause, *params)

async def count_cost_by_collection(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> int:
    query_suffix, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    count = await conn.fetchval(f"SELECT COUNT(DISTINCT c.id) {query_suffix}", *params)
    return count or 0

async def get_cost_by_file(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any], limit: int, offset: int) -> List[Dict[str, Any]]:
    query_suffix, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    join_clause = " LEFT JOIN cost_metric cm ON f.id = cm.file_id "
    select_clause = "SELECT f.name, f.size_bytes, cm.total_cost as cost "
    pagination_clause = f" ORDER BY cost DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
    params.extend([limit, offset])
    return await conn.fetch(select_clause + query_suffix + join_clause + pagination_clause, *params)

async def count_cost_by_file(conn: Connection, requesting_user: Dict[str, Any], active_ngroup_id: Optional[UUID], filters: Dict[str, Any]) -> int:
    query_suffix, params = _build_metrics_query_parts(requesting_user, active_ngroup_id, filters)
    count = await conn.fetchval(f"SELECT COUNT(f.id) {query_suffix}", *params)
    return count or 0
