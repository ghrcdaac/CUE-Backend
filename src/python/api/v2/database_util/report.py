
from asyncpg import Connection
from typing import List, Optional, Dict, Any
from uuid import UUID
import structlog
from datetime import date

logger = structlog.get_logger(__name__)
async def list_files_for_status_pdf_report_batch(
    conn: Connection,
    requesting_user: Dict[str, Any],
    active_ngroup_id: Optional[UUID],
    status: str,
    limit: int,
    offset: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """Retrieves one batch of files for the status PDF report."""
    user_roles = set(requesting_user.get('roles', []))
    params: list[Any] = [status]

    base_query = """
        SELECT
            f.id, f.name, f.type, f.size_bytes, f.collection_id, c.short_name AS collection_name,
            fs.status, fs.upload_time, fs.egress_start
        FROM file f
        JOIN collection c ON f.collection_id = c.id
        LEFT JOIN file_status fs ON f.id = fs.id
    """
    where_conditions = ["f.name != 'pending_upload'", "fs.status = $1"]

    if active_ngroup_id:
        params.append(active_ngroup_id)
        where_conditions.append(f"c.ngroup_id = ${len(params)}")
    else:
        if 'admin' not in user_roles and 'security' not in user_roles:
            where_conditions.append("FALSE")

    if start_date:
        params.append(start_date)
        where_conditions.append(f"fs.upload_time >= ${len(params)}")

    if end_date:
        params.append(end_date)
        where_conditions.append(f"fs.upload_time < (${len(params)}::date + 1)")

    query = f"""
        {base_query}
        WHERE {' AND '.join(where_conditions)}
        ORDER BY fs.upload_time DESC, f.id
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2};
    """
    params.extend([limit, offset])
    return await conn.fetch(query, *params)

