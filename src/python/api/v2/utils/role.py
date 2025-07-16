import uuid
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import role as role_db
from lambda_utils.type_util.role import RoleCreate, RoleReturn, RoleUpdate
from typing import List, Optional
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class RoleNotFoundError(Exception):
    def __init__(self, role_id: Optional[UUID] = None, short_name: Optional[str] = None, long_name: Optional[str] = None):
        if role_id:
            message = f"Role not found with ID: {role_id}"
        elif short_name:
            message = f"Role not found with short_name: {short_name}"
        elif long_name:
            message = f"Role not found with long_name: {long_name}"
        else:
            message = "Role not found"
        super().__init__(message)
        self.role_id = role_id
        self.short_name = short_name
        self.long_name = long_name

async def create_role(role: RoleCreate) -> RoleReturn:
    """Creates a new role record."""
    pool: Pool = await get_connection_pool()
    params = (role.short_name, role.long_name)
    try:
        result = await query(pool, role_db.create_role_in_db, params, row_mapper=RoleReturn.from_db_row)
        return result[0]
    except Exception as e:
        logger.error(f"Error creating role: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_role(role_id: UUID) -> RoleReturn | None:
    """Retrieves a role record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (role_id,)
    try:
        result = await query(pool, role_db.get_role_from_db, params, row_mapper=RoleReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise RoleNotFoundError(role_id=role_id)
    except Exception as e:
        logger.error(f"Error getting role: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def update_role(role_id: UUID, role_update: RoleUpdate) -> RoleReturn | None:
    """Updates an existing role record."""
    pool: Pool = await get_connection_pool()
    update_fields = {k: v for k, v in role_update.model_dump().items() if v is not None}
    if not update_fields:
        return await get_role(role_id)

    params = (update_fields, role_id)
    try:
        result = await query(pool, role_db.update_role_in_db, params, row_mapper=RoleReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise RoleNotFoundError(role_id=role_id)
    except Exception as e:
        logger.error(f"Error updating role: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def delete_role(role_id: UUID) -> bool:
    """Deletes a role record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (role_id,)
    try:
        result = await query(pool, role_db.delete_role_from_db, params)
        if not result:
            raise RoleNotFoundError(role_id=role_id)
        return result
    except Exception as e:
        logger.error(f"Error deleting role: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_roles() -> List[RoleReturn]:
    """Retrieves all role records."""
    pool: Pool = await get_connection_pool()
    try:
        results = await query(pool, role_db.list_roles_from_db, row_mapper=RoleReturn.from_db_row)
        return results
    except Exception as e:
        logger.error(f"Error listing roles: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_role_by_lookup(
    short_name: Optional[str] = None,
    long_name: Optional[str] = None
) -> RoleReturn | None:
    """Retrieves a role record by short_name or long_name."""
    if not short_name and not long_name:
        raise ValueError("Either short_name or long_name must be provided")

    pool: Pool = await get_connection_pool()
    params = (short_name, long_name)
    try:
        result = await query(pool, role_db.get_role_by_lookup_from_db, params, row_mapper=RoleReturn.from_db_row)
        if result:
            return result[0]
        else:
            if short_name:
                raise RoleNotFoundError(short_name=short_name)
            else:
                raise RoleNotFoundError(long_name=long_name)
    except Exception as e:
        logger.error(f"Error during role lookup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()