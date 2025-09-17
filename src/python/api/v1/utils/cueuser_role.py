from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import cueuser_role as cueuser_role_db
from lambda_utils.type_util.cueuser_role import CueuserRoleCreate, CueuserRoleReturn
from typing import List
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class CueuserRoleAssociationError(Exception):
    pass

class CueuserRoleNotFoundError(Exception):
    def __init__(self, cueuser_id: UUID, role_id: UUID):
        super().__init__(f"Association between Cueuser ID: {cueuser_id} and Role ID: {role_id} not found")
        self.cueuser_id = cueuser_id
        self.role_id = role_id

async def create_cueuser_role_association(data: CueuserRoleCreate) -> bool:
    """Associates a cueuser with a role."""
    pool: Pool = await get_connection_pool()
    params = (data.cueuser_id, data.role_id)
    try:
        result = await query(pool, cueuser_role_db.create_cueuser_role_association_in_db, params)
        return result
    except ValueError as e:
        logger.error(f"Error associating cueuser with role: {e}", exc_info=True)
        raise CueuserRoleAssociationError(f"Failed to associate cueuser with role: {e}")
    finally:
        await pool.close()

async def delete_cueuser_role_association(data: CueuserRoleCreate) -> bool:
    """Removes the association between a cueuser and a role."""
    pool: Pool = await get_connection_pool()
    params = (data.cueuser_id, data.role_id)
    try:
        result = await query(pool, cueuser_role_db.delete_cueuser_role_association_from_db, params)
        if not result:
            raise CueuserRoleNotFoundError(data.cueuser_id, data.role_id)
        return result
    except Exception as e:
        logger.error(f"Error removing association between cueuser and role: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_roles_for_cueuser(cueuser_id: UUID) -> List[UUID]:
    """Retrieves all role IDs associated with a cueuser."""
    pool: Pool = await get_connection_pool()
    params = (cueuser_id,)
    try:
        return await query(pool, cueuser_role_db.list_roles_for_cueuser_from_db, params)
    except Exception as e:
        logger.error(f"Error listing roles for cueuser: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_cueusers_with_role(role_id: UUID) -> List[UUID]:
    """Retrieves all cueuser IDs associated with a role."""
    pool: Pool = await get_connection_pool()
    params = (role_id,)
    try:
        return await query(pool, cueuser_role_db.list_cueusers_with_role_from_db, params)
    except Exception as e:
        logger.error(f"Error listing cueusers with role: {e}", exc_info=True)
        raise
    finally:
        await pool.close()