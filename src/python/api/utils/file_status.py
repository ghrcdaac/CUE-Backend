import json
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import file_status as file_status_db
from lambda_utils.type_util.file_status import FileStatusCreate, FileStatusReturn, FileStatusUpdate
from typing import List, Optional
from uuid import UUID
import logging
from datetime import datetime, timezone 

logger = logging.getLogger(__name__)

class FileStatusNotFoundError(Exception):
     def __init__(self, id: UUID):
        super().__init__(f"File status not found for file ID: {id}")
        self.id = id

async def create_file_status(file_status: FileStatusCreate) -> FileStatusReturn:
    """Creates a new file_status record."""
    pool: Pool = await get_connection_pool()
    upload_time = datetime.now(timezone.utc)
    scan_results_json = json.dumps(file_status.scan_results) if file_status.scan_results else None
    params = (file_status.id, upload_time, file_status.status, scan_results_json)
    try:
        result = await query(pool, file_status_db.create_file_status_in_db, params, row_mapper=FileStatusReturn.from_db_row)
        return result[0]
    except Exception as e:
        logger.error(f"Error creating file_status: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_file_status(id: UUID) -> FileStatusReturn | None:
    """Retrieves a file_status record by id."""
    pool: Pool = await get_connection_pool()
    params = (id,)
    try:
        result = await query(pool, file_status_db.get_file_status_from_db, params, row_mapper=FileStatusReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise FileStatusNotFoundError(id=id) 
    except Exception as e:
        logger.error(f"Error getting file_status: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def update_file_status(id: UUID, file_status_update: FileStatusUpdate) -> FileStatusReturn | None:
    """Updates an existing file_status record."""
    pool: Pool = await get_connection_pool()
    update_fields = {k: v for k, v in file_status_update.model_dump().items() if v is not None}
    if not update_fields:
        return await get_file_status(id)

    params = (update_fields, id)
    try:
        result = await query(pool, file_status_db.update_file_status_in_db, params, row_mapper=FileStatusReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise FileStatusNotFoundError(id=id) 
    except Exception as e:
        logger.error(f"Error updating file_status: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def delete_file_status(id: UUID) -> bool:
    """Deletes a file_status record by id."""
    pool: Pool = await get_connection_pool()
    params = (id,)  
    try:
        result = await query(pool, file_status_db.delete_file_status_from_db, params)
        if not result:
            raise FileStatusNotFoundError(id=id) 
        return result
    except Exception as e:
        logger.error(f"Error deleting file_status: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_file_statuses() -> List[FileStatusReturn]:
    """Retrieves all file_status records."""
    pool: Pool = await get_connection_pool()
    try:
        results = await query(pool, file_status_db.list_file_statuses_from_db, row_mapper=FileStatusReturn.from_db_row)
        return results
    except Exception as e:
        logger.error(f"Error listing file_statuses: {e}", exc_info=True)
        raise
    finally:
        await pool.close()