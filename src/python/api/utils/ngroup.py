import uuid
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import ngroup as ngroup_db
from lambda_utils.type_util.ngroup import NgroupCreate, NgroupReturn, NgroupUpdate
from typing import Optional, List
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class NgroupNotFoundError(Exception):
    def __init__(self, ngroup_id: Optional[UUID] = None, short_name: str = None, long_name: str = None):
        super().__init__(f"Ngroup not found with ID: {ngroup_id}, short_name: {short_name}, or long_name: {long_name}")
        self.ngroup_id = ngroup_id
        self.short_name = short_name
        self.long_name = long_name

async def create_ngroup(ngroup: NgroupCreate) -> NgroupReturn:
    """Creates a new ngroup record."""
    pool: Pool = await get_connection_pool()
    try:
        if ngroup.id is None:
            ngroup.id = uuid.uuid4()
        params = (ngroup.id, ngroup.short_name, ngroup.long_name)
        result = await query(pool, ngroup_db.create_ngroup_in_db, params, row_mapper=NgroupReturn.from_db_row)
        return result[0]
    except Exception as e:
        logger.error(f"Error creating ngroup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_ngroup_id_by_name(short_name: str = None, long_name: str = None) -> Optional[UUID]:
    """Retrieves the ngroup ID based on short_name or long_name."""
    if not short_name and not long_name:
        raise ValueError("Either short_name or long_name must be provided")

    pool: Pool = await get_connection_pool()
    params = (short_name, long_name)
    try:
        result = await query(pool, ngroup_db.get_ngroup_id_from_db, params)
        if result:
            return result
        else:
            raise NgroupNotFoundError(short_name=short_name, long_name=long_name)
    except Exception as e:
        logger.error(f"Error getting ngroup ID by name: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_ngroup(ngroup_id: UUID) -> NgroupReturn | None:
    """Retrieves an ngroup record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (ngroup_id,)
    try:
        result = await query(pool, ngroup_db.get_ngroup_from_db, params, row_mapper=NgroupReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise NgroupNotFoundError(ngroup_id=ngroup_id)
    except Exception as e:
        logger.error(f"Error getting ngroup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def update_ngroup(ngroup_id: UUID, ngroup_update: NgroupUpdate) -> NgroupReturn | None:
    """Updates an existing ngroup record."""
    pool: Pool = await get_connection_pool()
    params = (ngroup_id, ngroup_update.short_name, ngroup_update.long_name)
    try:
        result = await query(pool, ngroup_db.update_ngroup_in_db, params, row_mapper=NgroupReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise NgroupNotFoundError(ngroup_id=ngroup_id)
    except Exception as e:
        logger.error(f"Error updating ngroup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def delete_ngroup(ngroup_id: UUID) -> bool:
    """Deletes an ngroup record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (ngroup_id,)
    try:
        result = await query(pool, ngroup_db.delete_ngroup_from_db, params)
        if not result:
            raise NgroupNotFoundError(ngroup_id=ngroup_id)
        return result
    except Exception as e:
        logger.error(f"Error deleting ngroup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_ngroups() -> List[NgroupReturn]:
    """Retrieves all ngroup records."""
    pool: Pool = await get_connection_pool()
    try:
        results = await query(pool, ngroup_db.list_ngroups_from_db, None, row_mapper=NgroupReturn.from_db_row)
        return results
    except Exception as e:
        logger.error(f"Error listing ngroups: {e}", exc_info=True)
        raise
    finally:
        await pool.close()