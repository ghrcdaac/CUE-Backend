# utils/collection.py
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import collection as collection_db
from lambda_utils.type_util.collection import (CollectionCreate, CollectionReturn,
                                              CollectionUpdate,CollectionFileResponse,CollectionFileCount)
from lambda_utils.type_util.file import FileReturn
from typing import List, Optional, Tuple
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class CollectionNotFoundError(Exception):
    def __init__(self, collection_id: UUID = None, short_name: str = None, ngroup_id: UUID = None):
        if collection_id and ngroup_id:
            message = f"Collection not found with ID: {collection_id} and ngroup_id: {ngroup_id}"
        elif collection_id:
            message = f"Collection not found with ID: {collection_id}"
        elif short_name:
            message = f"Collection not found with short_name: {short_name}"
        else:
            message = "Collection not found"
        super().__init__(message)
        self.collection_id = collection_id
        self.short_name = short_name
        self.ngroup_id = ngroup_id

async def create_collection(collection: CollectionCreate) -> CollectionReturn:
    """Creates a new collection record."""
    pool: Pool = await get_connection_pool()
    params = (collection.ngroup_id, collection.egress_id, collection.short_name, collection.provider_id, collection.active)
    try:
        result = await query(pool, collection_db.create_collection_in_db, params, row_mapper=CollectionReturn.from_db_row)
        return result[0]
    except Exception as e:
        logger.error(f"Error creating collection: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_collection(collection_id: UUID, ngroup_id: UUID) -> CollectionReturn | None:
    """Retrieves a collection record by its ID, filtered by ngroup_id."""
    pool: Pool = await get_connection_pool()
    params = (collection_id, ngroup_id)  # Pass ngroup_id
    try:
        result = await query(pool, collection_db.get_collection_from_db, params, row_mapper=CollectionReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise CollectionNotFoundError(collection_id=collection_id, ngroup_id=ngroup_id)
    except Exception as e:
        logger.error(f"Error getting collection: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_collection_by_lookup(short_name: str, ngroup_id: UUID) -> CollectionReturn | None:
    """Retrieves a collection record by short_name, filtered by ngroup_id."""
    pool: Pool = await get_connection_pool()
    params = (short_name, ngroup_id) # Pass ngroup_id
    try:
        result = await query(pool, collection_db.get_collection_by_lookup_from_db, params, row_mapper=CollectionReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise CollectionNotFoundError(short_name=short_name, ngroup_id=ngroup_id)
    except Exception as e:
        logger.error(f"Error during collection lookup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_collection_files_count(ngroup_id: UUID, page_size: int, page: int) -> CollectionFileResponse | None:
    """Retrieves a collection by file_count, filtered by ngroup_id."""
    pool: Pool = await get_connection_pool()
    offset = (page - 1) * page_size
    params = (ngroup_id, page_size, offset) # Pass ngroup_id
    try:
        total_count = await get_collection_files_total_count(ngroup_id)
        if total_count > 0:
            result = await query(pool, collection_db.get_collection_files_count, params)
            if result:
                file_counts = [
                        CollectionFileCount(
                            id=row["collection_id"],
                            name=row["short_name"],
                            file_count=row["file_count"]
                        )
                        for row in result
                ]

                return CollectionFileResponse(
                    ngroup_id=result[0]["ngroup_id"],
                    page=page,
                    total_count=total_count,
                    files_by_count=file_counts
                )
            else:
                raise Exception
        else:
            return CollectionFileResponse(
                ngroup_id=ngroup_id,
                page=page,
                total_count=0,
                files_by_count=[]
        )
    except Exception as e:
        logger.error(f"Error during collection lookup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_collection_files_total_count(ngroup_id: UUID):
    pool: Pool = await get_connection_pool()
    params = (ngroup_id)
    try:
        result = await query(pool, collection_db.get_collection_total_count_by_files, params)
        if result:
            return result
        else:
            raise Exception
    except Exception as e:
        logger.error(f"Error during collection lookup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

    

async def update_collection(collection_id: UUID, collection_update: CollectionUpdate) -> CollectionReturn | None:
    """Updates an existing collection record."""
    # No changes needed here, as updates don't depend on ngroup_id for uniqueness
    pool: Pool = await get_connection_pool()
    update_fields = {k: v for k, v in collection_update.model_dump().items() if v is not None}
    if not update_fields:
        return await get_collection(collection_id)  # No ngroup_id needed for update check

    params = (update_fields, collection_id)
    try:
        result = await query(pool, collection_db.update_collection_in_db, params, row_mapper=CollectionReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise CollectionNotFoundError(collection_id=collection_id)
    except Exception as e:
        logger.error(f"Error updating collection: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def delete_collection(collection_id: UUID, ngroup_id: UUID) -> bool:
    """Deletes a collection record by its ID, filtered by ngroup_id."""
    pool: Pool = await get_connection_pool()
    params = (collection_id, ngroup_id)  # Pass ngroup_id
    try:
        result = await query(pool, collection_db.delete_collection_from_db, params)
        if not result:
             raise CollectionNotFoundError(collection_id=collection_id, ngroup_id=ngroup_id)
        return result
    except Exception as e:
        logger.error(f"Error deleting collection: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_collections(ngroup_id: UUID) -> List[CollectionReturn]:
    """Retrieves all collection records, filtered by ngroup_id."""
    pool: Pool = await get_connection_pool()
    params = (ngroup_id,)  # Pass ngroup_id as a tuple
    try:
        results = await query(pool, collection_db.list_collections_from_db, params, row_mapper=CollectionReturn.from_db_row)
        return results
    except Exception as e:
        logger.error(f"Error listing collections: {e}", exc_info=True)
        raise
    finally:
        await pool.close()


async def list_files_for_collection(collection_id: UUID, ngroup_id: UUID, page: int, page_size: int) -> Tuple[List[FileReturn], int]:
    """Lists files for a collection, filtered by ngroup_id, with pagination."""
    pool: Pool = await get_connection_pool()
    offset = (page - 1) * page_size
    params = (collection_id, ngroup_id, page_size, offset)  # Pass ngroup_id

    try:
        # Fetch files for the current page
        files = await query(pool, collection_db.list_files_for_collection_from_db, params, row_mapper=FileReturn.from_db_row)

        # Fetch total count of files for the collection (without pagination)
        total_count_result = await query(pool, collection_db.count_files_for_collection_from_db, (collection_id,ngroup_id))
        total_count = total_count_result if total_count_result else 0

        return files, total_count
    except Exception as e:
        logger.error(f"Error listing files for collection: {e}", exc_info=True)
        raise
    finally:
        await pool.close()