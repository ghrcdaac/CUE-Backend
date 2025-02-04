from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import file_status as file_status_db
from lambda_utils.type_util.file_status import FileStatusCreate, FileStatusReturn, FileStatusUpdate
from typing import List, Optional
import uuid
from uuid import UUID
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class FileStatusNotFoundError(Exception):
    def __init__(self, file_status_id: UUID):
        super().__init__(f"File status not found with ID: {file_status_id}")
        self.file_status_id = file_status_id

async def create_file_status(file_status: FileStatusCreate) -> FileStatusReturn:
    """Creates a new file_status record."""
    pool: Pool = await get_connection_pool()
    file_status_id = uuid.uuid4()
    params = (file_status_id, file_status.file_id, datetime.now(timezone.utc), file_status.status, file_status.scan_results)  
    try:
        result = await query(pool, file_status_db.create_file_status_in_db, params, row_mapper=FileStatusReturn.from_db_row)
        return result[0]
    except Exception as e:
        logger.error(f"Error creating file_status: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_file_status(file_status_id: UUID) -> FileStatusReturn | None:
    """Retrieves a file_status record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (file_status_id,)
    try:
        result = await query(pool, file_status_db.get_file_status_from_db, params, row_mapper=FileStatusReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise FileStatusNotFoundError(file_status_id=file_status_id)
    except Exception as e:
        logger.error(f"Error getting file_status: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def update_file_status(file_status_id: UUID, file_status_update: FileStatusUpdate) -> FileStatusReturn | None:
    """Updates an existing file_status record."""
    pool: Pool = await get_connection_pool()
    update_fields = {k: v for k, v in file_status_update.model_dump().items() if v is not None}
    if not update_fields:
        return await get_file_status(file_status_id)

    params = (update_fields, file_status_id)
    try:
        result = await query(pool, file_status_db.update_file_status_in_db, params, row_mapper=FileStatusReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise FileStatusNotFoundError(file_status_id=file_status_id)
    except Exception as e:
        logger.error(f"Error updating file_status: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def delete_file_status(file_status_id: UUID) -> bool:
    """Deletes a file_status record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (file_status_id,)
    try:
        result = await query(pool, file_status_db.delete_file_status_from_db, params)
        if not result:
            raise FileStatusNotFoundError(file_status_id=file_status_id)
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