from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import collection as collection_db
from lambda_utils.type_util.collection import CollectionCreate, CollectionReturn, CollectionUpdate
from lambda_utils.type_util.file import FileReturn
from typing import List, Optional, Tuple
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class CollectionNotFoundError(Exception):
    def __init__(self, collection_id: UUID = None, short_name: str = None):
        if collection_id:
            message = f"Collection not found with ID: {collection_id}"
        elif short_name:
            message = f"Collection not found with short_name: {short_name}"
        else:
            message = "Collection not found"
        super().__init__(message)
        self.collection_id = collection_id
        self.short_name = short_name

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

async def get_collection(collection_id: UUID) -> CollectionReturn | None:
    """Retrieves a collection record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (collection_id,)
    try:
        result = await query(pool, collection_db.get_collection_from_db, params, row_mapper=CollectionReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise CollectionNotFoundError(collection_id=collection_id)
    except Exception as e:
        logger.error(f"Error getting collection: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_collection_by_lookup(short_name: str) -> CollectionReturn | None:
    """Retrieves a collection record by short_name."""
    pool: Pool = await get_connection_pool()
    params = (short_name,)
    try:
        result = await query(pool, collection_db.get_collection_by_lookup_from_db, params, row_mapper=CollectionReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise CollectionNotFoundError(short_name=short_name)
    except Exception as e:
        logger.error(f"Error during collection lookup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def update_collection(collection_id: UUID, collection_update: CollectionUpdate) -> CollectionReturn | None:
    """Updates an existing collection record."""
    pool: Pool = await get_connection_pool()
    update_fields = {k: v for k, v in collection_update.model_dump().items() if v is not None}
    if not update_fields:
        return await get_collection(collection_id)

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

async def delete_collection(collection_id: UUID) -> bool:
    """Deletes a collection record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (collection_id,)
    try:
        result = await query(pool, collection_db.delete_collection_from_db, params)
        if not result:
            raise CollectionNotFoundError(collection_id=collection_id)
        return result
    except Exception as e:
        logger.error(f"Error deleting collection: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_collections() -> List[CollectionReturn]:
    """Retrieves all collection records."""
    pool: Pool = await get_connection_pool()
    try:
        results = await query(pool, collection_db.list_collections_from_db, row_mapper=CollectionReturn.from_db_row)
        return results
    except Exception as e:
        logger.error(f"Error listing collections: {e}", exc_info=True)
        raise
    finally:
        await pool.close()


async def list_files_for_collection(collection_id: UUID, page: int, page_size: int) -> Tuple[List[FileReturn], int]:
    """Lists files associated with a collection, including pagination and total count."""
    pool: Pool = await get_connection_pool()
    offset = (page - 1) * page_size
    params = (collection_id, page_size, offset)

    try:
        # Fetch the files for the current page, using FileReturn.from_db_row as the row_mapper
        files = await query(pool, collection_db.list_files_for_collection_from_db, params, row_mapper=FileReturn.from_db_row)

        # Fetch the total count of files for the collection
        total_count_result = await query(pool, collection_db.count_files_for_collection_from_db, (collection_id,))
        total_count = total_count_result[0]['count'] if total_count_result else 0

        return files, total_count
    except Exception as e:
        logger.error(f"Error listing files for collection: {e}", exc_info=True)
        raise
    finally:
        await pool.close()