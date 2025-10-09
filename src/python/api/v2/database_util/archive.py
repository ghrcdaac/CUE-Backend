# File: src/python/api/v2/database_util/archive.py

from asyncpg import Connection
from typing import List, Dict, Any
from uuid import UUID
from .file_metrics import _build_metrics_query_parts # Re-use the powerful query builder
import structlog

logger = structlog.get_logger(__name__)

async def get_file_ids_by_filter(conn: Connection, ngroup_id: UUID, filters: Dict[str, Any]) -> List[UUID]:
    """
    Securely queries the main Postgres DB to get a list of file IDs
    that match the specified filter criteria.
    """
    from_clause, where_clause, params = _build_metrics_query_parts({},ngroup_id, filters)
    full_query = "SELECT f.id " + from_clause + where_clause
    
    records = await conn.fetch(full_query, *params)
    return [record['id'] for record in records]