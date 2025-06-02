from asyncpg import Connection
from typing import List, Dict, Optional, Tuple, Any
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

async def _build_metrics_query_parts(
    ngroup_id: UUID,
    optional_filters: Dict[str, Any],
    mandatory_conditions: Optional[Dict[str, Any]] = None
) -> Tuple[str, List[Any]]:
    """
    Helper to build WHERE clauses and parameters for metric/listing queries.
    Requires ngroup_id, handles optional filters and conditions.
    End date is treated as inclusive.
    """
    where_clauses = []
    params: List[Any] = []
    param_index = 1

    base_query = """
        FROM file f
        JOIN file_status fs ON f.id = fs.id
        JOIN collection c ON f.collection_id = c.id
    """
    joins = ""

    where_clauses.append(f"c.ngroup_id = ${param_index}")
    params.append(ngroup_id)
    param_index += 1

    if mandatory_conditions:
        for field, value in mandatory_conditions.items():
            where_clauses.append(f"{field} = ${param_index}")
            params.append(value)
            param_index += 1

    if optional_filters.get("start_date"):
        where_clauses.append(f"fs.upload_time >= ${param_index}")
        params.append(optional_filters["start_date"])
        param_index += 1
    if optional_filters.get("end_date"):
        where_clauses.append(f"DATE(fs.upload_time) <= ${param_index}")
        params.append(optional_filters["end_date"])
        param_index += 1
    if optional_filters.get("user_id"):
        where_clauses.append(f"f.cueuser_uploaded = ${param_index}")
        params.append(optional_filters["user_id"])
        param_index += 1
    if optional_filters.get("collection_id"):
        where_clauses.append(f"f.collection_id = ${param_index}")
        params.append(optional_filters["collection_id"])
        param_index += 1
    if optional_filters.get("provider_id"):
        where_clauses.append(f"c.provider_id = ${param_index}")
        params.append(optional_filters["provider_id"])
        param_index += 1

    query_suffix = base_query + joins
    if where_clauses:
        query_suffix += " WHERE " + " AND ".join(where_clauses)

    return query_suffix, params

async def get_daily_metrics(conn: Connection, ngroup_id:UUID, filters: Dict[str, Any]) -> List:
    query_suffix, params = await _build_metrics_query_parts(ngroup_id, filters)
    select_clause = "SELECT DATE(fs.upload_time) as date, SUM(f.size_bytes) as size, SUM(EXTRACT(EPOCH FROM (scan_end - scan_start))) as scan_duration, count(f.id) as file_count"
    groupby_clause = " GROUP BY DATE(fs.upload_time)"
    full_query = select_clause + query_suffix + groupby_clause
    try:
        return await conn.fetch(full_query, *params)
    except Exception as e:
        logger.error(f"Error fetching daily metrics: {e}", exc_info=True)
        raise

async def get_collection_metrics(conn: Connection, ngroup_id:UUID, filters: Dict[str, Any], limit:int, offset:int) -> List:
    query_suffix, params = await _build_metrics_query_parts(ngroup_id, filters)
    select_clause = "SELECT c.short_name as name, SUM(f.size_bytes) as size, SUM(EXTRACT(EPOCH FROM (fs.scan_end - fs.scan_start))) as scan_duration "
    limit_param_index = len(params) + 1
    offset_param_index = len(params) + 2
    params.extend([limit, offset])
    groupby_clause = " GROUP BY f.collection_id, c.short_name"
    pagination_clause = f" LIMIT ${limit_param_index} OFFSET ${offset_param_index}"
    orderby_clause = " ORDER BY c.short_name"
    full_query = select_clause + query_suffix + groupby_clause + orderby_clause + pagination_clause
    try:
        return await conn.fetch(full_query, *params)
    except Exception as e:
        logger.error(f"Error fetching collection metrics: {e}", exc_info=True)
        raise

async def count_collection_metrics(conn: Connection, ngroup_id:UUID, filters: Dict[str, Any]) -> int:
    query_suffix, params = await _build_metrics_query_parts(ngroup_id, filters)
    select_clause = "SELECT COUNT(DISTINCT(c.id)) "
    full_query = select_clause + query_suffix
    try:
        count = await conn.fetchval(full_query, *params)
        return int(count) if count is not None else 0
    except Exception as e:
        logger.error(f"Error counting collection metrics: {e}", exc_info=True)
        raise

async def get_file_metrics(conn: Connection, ngroup_id:UUID, filters: Dict[str, Any], limit:int, offset:int) -> List:
    query_suffix, params = await _build_metrics_query_parts(ngroup_id, filters)
    select_clause = "SELECT f.name as name, f.size_bytes as size, EXTRACT(EPOCH FROM (fs.scan_end - fs.scan_start)) as scan_duration "
    limit_param_index = len(params) + 1
    offset_param_index = len(params) + 2
    params.extend([limit, offset])
    pagination_clause = f" LIMIT ${limit_param_index} OFFSET ${offset_param_index}"
    orderby_clause = " ORDER BY size"
    full_query = select_clause + query_suffix + orderby_clause + pagination_clause
    try:
        return await conn.fetch(full_query, *params)
    except Exception as e:
        logger.error(f"Error fetching file metrics: {e}", exc_info=True)
        raise

async def count_file_metrics(conn: Connection, ngroup_id:UUID, filters: Dict[str, Any]) -> int:
    query_suffix, params = await _build_metrics_query_parts(ngroup_id, filters)
    select_clause = "SELECT COUNT(f.id) "
    full_query = select_clause + query_suffix
    try:
        count = await conn.fetchval(full_query, *params)
        return int(count) if count is not None else 0
    except Exception as e:
        logger.error(f"Error fetching file metrics: {e}", exc_info=True)
        raise