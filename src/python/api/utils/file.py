# utils/file.py
import json
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import file as file_db
from lambda_utils.database_util import collection as collection_db # Needed for ngroup check
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

class AuthorizationError(Exception): # Custom error for auth checks
    def __init__(self, message="User not authorized for this operation or resource."):
        super().__init__(message)


# --- Helper Function ---
async def get_ngroup_id_for_file(file_id: UUID) -> Optional[UUID]:
     """Gets the ngroup_id associated with a given file_id."""
     pool: Pool = await get_connection_pool()
     try:
          async with pool.acquire() as conn:
               ngroup_id = await file_db.get_ngroup_id_for_file_db(conn, file_id)
          if not ngroup_id:
               # File might not exist, or join failed unexpectedly
               logger.warning(f"Could not retrieve ngroup for file_id: {file_id}")
               return None
          return ngroup_id
     except Exception as e:
          logger.error(f"Error getting ngroup ID for file {file_id}: {e}", exc_info=True)
          raise # Re-raise db errors
     finally:
          pool.release(conn)


# --- CRUD Functions ---

async def create_file(file: FileCreate, user_ngroup_id: UUID) -> FileReturn:
    """Creates a new file record, verifying collection belongs to user's ngroup."""
    pool: Pool = await get_connection_pool()
    # Verify collection exists and belongs to the user's ngroup
    try:
        async with pool.acquire() as conn:
             collection_row = await collection_db.get_collection_from_db(conn, (file.collection_id, user_ngroup_id))
             if not collection_row:
                  raise AuthorizationError(f"Collection {file.collection_id} not found or does not belong to user's group {user_ngroup_id}.")

             params = (str(uuid7()),file.name, file.type, file.cueuser_uploaded, file.size_bytes, file.collection_id, file.edpub, file.checksum)
             result = await file_db.create_file_in_db(conn, params) # Use the acquired connection

        if not result: # Should not happen if DB call is correct
             raise Exception("Failed to create file record after verification.")
        return FileReturn.from_db_row(result[0])

    except AuthorizationError: # Re-raise specific auth errors
        raise
    except ValueError: # Catch DB value errors (duplicate, bad FK)
         raise
    except Exception as e:
        logger.error(f"Error creating file: {e}", exc_info=True)
        raise # Re-raise other unexpected errors
    finally:
        pool.release(conn)

async def get_file(file_id: UUID) -> FileReturn:
    """Retrieves a file record by its ID. Authorization check happens in endpoint."""
    pool: Pool = await get_connection_pool()
    params = (file_id,)
    try:
        # Note: This doesn't check ngroup, endpoint should verify first
        result = await query(pool, file_db.get_file_from_db, params, row_mapper=FileReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise FileNotFoundError(file_id=file_id)
    except FileNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting file {file_id}: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_files_by_name(name: str, ngroup_id: UUID) -> List[FileReturn]:
    """Retrieves a list of file records by name for a specific ngroup."""
    pool: Pool = await get_connection_pool()
    try:
        results = await query(pool, file_db.get_files_by_name_from_db, (name, ngroup_id), row_mapper=FileReturn.from_db_row)
        # DB query already filters by ngroup, no FileNotFoundError needed if list is empty
        return results
    except Exception as e:
        logger.error(f"Error during file lookup by name '{name}' for ngroup {ngroup_id}: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def update_file(file_id: UUID, file_update: FileUpdate) -> FileReturn:
    """Updates an existing file record. Authorization check happens in endpoint."""
    pool: Pool = await get_connection_pool()
    update_fields = {k: v for k, v in file_update.model_dump(exclude_none=True)}
    if not update_fields:
         # If no fields to update, get and return current record
         # Need to call get_file, but ngroup check happens in endpoint
         # This path might need rethinking if get_file requires ngroup
         try:
              return await get_file(file_id)
         except FileNotFoundError:
              raise # Propagate if file doesn't exist at all

    params = (update_fields, file_id)
    try:
        # Note: This doesn't check ngroup, endpoint should verify first
        result = await query(pool, file_db.update_file_in_db, params, row_mapper=FileReturn.from_db_row)
        if result:
            return result[0]
        else:
            # Should not happen if update query is correct and record existed
            raise FileNotFoundError(file_id=file_id)
    except (FileNotFoundError, ValueError): # Catch expected errors
        raise
    except Exception as e:
        logger.error(f"Error updating file {file_id}: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def delete_file(file_id: UUID) -> bool:
    """Deletes a file record by its ID. Authorization check happens in endpoint."""
    pool: Pool = await get_connection_pool()
    params = (file_id,)
    try:
         # Note: This doesn't check ngroup, endpoint should verify first
        result = await query(pool, file_db.delete_file_from_db, params)
        if not result:
            raise FileNotFoundError(file_id=file_id)
        return result # Should be True if deletion succeeded
    except FileNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_files(ngroup_id: UUID) -> List[FileReturn]:
    """Retrieves all file records for a specific ngroup."""
    pool: Pool = await get_connection_pool()
    try:
        results = await query(pool, file_db.list_files_from_db, (ngroup_id,), row_mapper=FileReturn.from_db_row)
        return results
    except Exception as e:
        logger.error(f"Error listing files for ngroup {ngroup_id}: {e}", exc_info=True)
        raise
    finally:
        await pool.close()