# ./src/python/event_lambdas/update_cost/db.py

import os
from typing import Dict, List, Any
from asyncpg import Connection
import structlog

logger = structlog.get_logger(__name__)

async def get_file_data(conn: Connection, params: tuple) -> Dict[str,Any]:
    """ Get uploaded file ids and total upload volume within the time range"""
    select_files_query = """
        SELECT SUM(f.size_bytes) as total_size, ARRAY_AGG(JSON_BUILD_OBJECT('file_id', f.id, 'file_size', f.size_bytes)) as files
        FROM file f JOIN file_status fs ON f.id = fs.id
        WHERE fs.upload_time >= $1 AND fs.upload_time < $2;
    """
    try:
        file_data = {}
        results = await conn.fetchrow(select_files_query, *params)
        file_data["total_size"] = results['total_size']
        file_data["files"] = results['files']
        return file_data
    except Exception as e:
        logger.error("Error getting files.", exc_info=True)
        raise e

async def update_file_status_with_cost(conn: Connection, params:List[tuple]):
    """Bulk update the file status table with cost for each file in the params list"""
    update_query = """
        UPDATE file_status SET scan_results = scan_results::jsonb|| $2 WHERE id = $1  
    """
    try:
        await conn.executemany(update_query, params)
    except Exception as e:
        logger.error("Unable to update files with cost", e=e)


