
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import ngroup as ngroup_db
from lambda_utils.type_util.ngroup import NgroupCreate, NgroupReturn, NgroupUpdate
from typing import Optional, List
from uuid import UUID, uuid4

async def create_ngroup(ngroup: NgroupCreate) -> NgroupReturn:
    """Creates a new ngroup record."""
    pool: Pool = await get_connection_pool()
    if ngroup.id is None:
        ngroup.id = uuid4()
    params = (ngroup.id, ngroup.short_name, ngroup.long_name)
    result = await query(pool, ngroup_db.create_ngroup_in_db, params, row_mapper=NgroupReturn.from_db_row)
    await pool.close()
    return result[0]

async def get_ngroup_id_by_name(short_name: str = None, long_name: str = None) -> Optional[UUID]:
    """Retrieves the ngroup ID based on short_name or long_name."""
    if not short_name and not long_name:
        raise ValueError("Either short_name or long_name must be provided")

    pool: Pool = await get_connection_pool()
    params = (short_name, long_name)
    result = await query(pool, ngroup_db.get_ngroup_id_from_db, params)
    await pool.close()
    return result if result else None

async def get_ngroup(ngroup_id: UUID) -> NgroupReturn | None:
    """Retrieves an ngroup record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (ngroup_id,)
    result = await query(pool, ngroup_db.get_ngroup_from_db, params, row_mapper=NgroupReturn.from_db_row)
    await pool.close()
    return result[0] if result else None

async def update_ngroup(ngroup_id: UUID, ngroup_update: NgroupUpdate) -> NgroupReturn | None:
    """Updates an existing ngroup record."""
    pool: Pool = await get_connection_pool()
    params = (ngroup_id, ngroup_update.short_name, ngroup_update.long_name)
    result = await query(pool, ngroup_db.update_ngroup_in_db, params, row_mapper=NgroupReturn.from_db_row)
    await pool.close()
    return result[0] if result else None

async def delete_ngroup(ngroup_id: UUID) -> bool:
    """Deletes an ngroup record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (ngroup_id,)
    result = await query(pool, ngroup_db.delete_ngroup_from_db, params)
    await pool.close()
    return result

async def list_ngroups() -> List[NgroupReturn]:
    """Retrieves all ngroup records."""
    pool: Pool = await get_connection_pool()
    params = () # Pass params
    results = await query(pool, ngroup_db.list_ngroups_from_db, params, row_mapper=NgroupReturn.from_db_row)
    await pool.close()
    return results