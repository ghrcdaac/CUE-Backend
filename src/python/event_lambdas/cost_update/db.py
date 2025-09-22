# ./src/python/event_lambdas/update_cost/db.py

import os
from typing import List
from asyncpg import Connection
import structlog

logger = structlog.get_logger(__name__)

async def get_files_sizes(conn: Connection, params: tuple) -> List:
    """ Get the uploaded files' sizes with the date range"""
    select_files_query = """
            SELECT f.id, f.size_bytes
            FROM file f JOIN file_status fs ON f.id = fs.id
            WHERE DATE(fs.upload_time) >= $1 AND DATE(fs.upload_time) < $2 
    """
    try:
        file_sizes = await conn.fetch(select_files_query, *params)
         
        return file_sizes
    except Exception as e:
        logger.error("Error getting files.", exc_info=True)
        raise e

async def update_file_status_with_cost(conn: Connection, params:tuple):
    """ Update a file scan_results with aws cost """
    update_query = """
        UPDATE file_status SET scan_results = scan_results::jsonb|| $2 WHERE id = $1  
    """
    try:
        await conn.execute(update_query, *params)
    except Exception as e:
        logger.error(f"Error updating cost on file {params[0]}", exc_info=True)
        raise e

    