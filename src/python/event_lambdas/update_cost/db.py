# ./src/python/event_lambdas/update_cost/db.py

import logging
import os
from typing import List
from asyncpg import Connection

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

async def get_files_sizes(conn: Connection, params: tuple) -> List:
    """ Get the uploaded files' sizes with the date range"""
    select_files_query = """
            SELECT f.id, f.size_bytes
            FROM file f JOIN file_status fs ON f.id = fs.id
            WHERE DATE(fs.upload_time) >= $1 AND DATE(fs.upload_time) < $2 
                  AND NOT EXISTS(
                    SELECT 1 FROM JSONB_ARRAY_ELEMENTS(scan_results) AS elem 
	                WHERE elem ? 'unblended_cost' AND elem ? 'net_unblended_cost' AND elem ? 'net_amortized_cost')
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
