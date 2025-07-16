from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import privilege as privilege_db
from lambda_utils.type_util.privilege import PrivilegeCreate, PrivilegeReturn, PrivilegeUpdate
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class PrivilegeNotFoundError(Exception):
    def __init__(self, privilege: str):
        super().__init__(f"Privilege not found: {privilege}")
        self.privilege = privilege

async def create_privilege(privilege: PrivilegeCreate) -> PrivilegeReturn:
    """Creates a new privilege record."""
    pool: Pool = await get_connection_pool()
    params = (privilege.privilege,)
    try:
        result = await query(pool, privilege_db.create_privilege_in_db, params, row_mapper=PrivilegeReturn.from_db_row)
        return result[0]
    except Exception as e:
        logger.error(f"Error creating privilege: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_privilege(privilege_name: str) -> PrivilegeReturn | None:
    """Retrieves a privilege record by its name."""
    pool: Pool = await get_connection_pool()
    params = (privilege_name,)
    try:
        result = await query(pool, privilege_db.get_privilege_from_db, params, row_mapper=PrivilegeReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise PrivilegeNotFoundError(privilege=privilege_name)
    except Exception as e:
        logger.error(f"Error getting privilege: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def update_privilege(privilege_name: str, privilege_update: PrivilegeUpdate) -> PrivilegeReturn | None:
    """Updates an existing privilege record."""
    pool: Pool = await get_connection_pool()
    params = (privilege_update.privilege, privilege_name)
    try:
        result = await query(pool, privilege_db.update_privilege_in_db, params, row_mapper=PrivilegeReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise PrivilegeNotFoundError(privilege=privilege_name)
    except Exception as e:
        logger.error(f"Error updating privilege: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def delete_privilege(privilege_name: str) -> bool:
    """Deletes a privilege record by its name."""
    pool: Pool = await get_connection_pool()
    params = (privilege_name,)
    try:
        result = await query(pool, privilege_db.delete_privilege_from_db, params)
        if not result:
            raise PrivilegeNotFoundError(privilege=privilege_name)
        return result
    except Exception as e:
        logger.error(f"Error deleting privilege: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_privileges() -> List[PrivilegeReturn]:
    """Retrieves all privilege records."""
    pool: Pool = await get_connection_pool()
    try:
        results = await query(pool, privilege_db.list_privileges_from_db, row_mapper=PrivilegeReturn.from_db_row)
        return results
    except Exception as e:
        logger.error(f"Error listing privileges: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_privilege_by_lookup(
    privilege: Optional[str] = None
) -> PrivilegeReturn | None:
    """Retrieves a privilege record by name."""
    pool: Pool = await get_connection_pool()
    params = (privilege, )
    try:
        result = await query(pool, privilege_db.get_privilege_by_lookup_from_db, params, row_mapper=PrivilegeReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise PrivilegeNotFoundError(privilege=privilege)
    except Exception as e:
        logger.error(f"Error during privilege lookup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()