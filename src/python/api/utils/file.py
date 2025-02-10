from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import file as file_db
from lambda_utils.type_util.file import FileCreate, FileReturn, FileUpdate
from typing import List, Optional, Tuple
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class FileNotFoundError(Exception):
    def __init__(self, file_id: UUID = None, name: str = None):
        if file_id:
            message = f"File not found with ID: {file_id}"
        elif name:
            message = f"File not found with name: {name}"
        else:
            message = "File not found"
        super().__init__(message)
        self.file_id = file_id
        self.name = name

async def create_file(file: FileCreate) -> FileReturn:
    """Creates a new file record."""
    pool: Pool = await get_connection_pool()
    params = (file.name, file.type, file.cueuser_uploaded, file.size_bytes, file.collection_id, file.edpub, file.checksum)
    try:
        result = await query(pool, file_db.create_file_in_db, params, row_mapper=FileReturn.from_db_row)
        return result[0]
    except Exception as e:
        logger.error(f"Error creating file: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_file(file_id: UUID) -> FileReturn | None:
    """Retrieves a file record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (file_id,)
    try:
        result = await query(pool, file_db.get_file_from_db, params, row_mapper=FileReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise FileNotFoundError(file_id=file_id)
    except Exception as e:
        logger.error(f"Error getting file: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_files_by_name(name: str) -> List[FileReturn]:
    """Retrieves a list of file records by their name."""
    pool: Pool = await get_connection_pool()
    params = (name,)
    try:
        results = await query(pool, file_db.get_files_by_name_from_db, params, row_mapper=FileReturn.from_db_row)
        if results:
            return results
        else:
            raise FileNotFoundError(name=name)
    except Exception as e:
        logger.error(f"Error during file lookup by name: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def update_file(file_id: UUID, file_update: FileUpdate) -> FileReturn | None:
    """Updates an existing file record."""
    pool: Pool = await get_connection_pool()
    update_fields = {k: v for k, v in file_update.model_dump().items() if v is not None}
    if not update_fields:
        return await get_file(file_id)

    params = (update_fields, file_id)
    try:
        result = await query(pool, file_db.update_file_in_db, params, row_mapper=FileReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise FileNotFoundError(file_id=file_id)
    except Exception as e:
        logger.error(f"Error updating file: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def delete_file(file_id: UUID) -> bool:
    """Deletes a file record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (file_id,)
    try:
        result = await query(pool, file_db.delete_file_from_db, params)
        if not result:
            raise FileNotFoundError(file_id=file_id)
        return result
    except Exception as e:
        logger.error(f"Error deleting file: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_files() -> List[FileReturn]:
    """Retrieves all file records."""
    pool: Pool = await get_connection_pool()
    try:
        results = await query(pool, file_db.list_files_from_db, row_mapper=FileReturn.from_db_row)
        return results
    except Exception as e:
        logger.error(f"Error listing files: {e}", exc_info=True)
        raise
    finally:
        await pool.close()