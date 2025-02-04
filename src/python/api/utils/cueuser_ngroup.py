from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import cueuser_ngroup as cueuser_ngroup_db
from lambda_utils.type_util.cueuser_ngroup import CueuserNgroupCreate, CueuserNgroupReturn
from typing import List
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class CueuserNgroupAssociationError(Exception):
    pass

class CueuserNgroupNotFoundError(Exception):
    def __init__(self, cueuser_id: UUID, ngroup_id: UUID):
        super().__init__(f"Association between Cueuser ID: {cueuser_id} and Ngroup ID: {ngroup_id} not found")
        self.cueuser_id = cueuser_id
        self.ngroup_id = ngroup_id

async def create_cueuser_ngroup_association(cueuser_ngroup: CueuserNgroupCreate) -> bool:
    """Associates a cueuser with an ngroup."""
    pool: Pool = await get_connection_pool()
    params = (cueuser_ngroup.cueuser_id, cueuser_ngroup.ngroup_id)
    try:
        result = await query(pool, cueuser_ngroup_db.create_cueuser_ngroup_association_in_db, params)
        return result
    except ValueError as e:
        logger.error(f"Error associating cueuser with ngroup: {e}", exc_info=True)
        raise CueuserNgroupAssociationError(f"Failed to associate cueuser with ngroup: {e}")
    finally:
        await pool.close()

async def delete_cueuser_ngroup_association(cueuser_ngroup: CueuserNgroupCreate) -> bool:
    """Removes the association between a cueuser and an ngroup."""
    pool: Pool = await get_connection_pool()
    params = (cueuser_ngroup.cueuser_id, cueuser_ngroup.ngroup_id)
    try:
        result = await query(pool, cueuser_ngroup_db.delete_cueuser_ngroup_association_from_db, params)
        if not result:
            raise CueuserNgroupNotFoundError(cueuser_ngroup.cueuser_id, cueuser_ngroup.ngroup_id)
        return result
    except Exception as e:
        logger.error(f"Error removing association between cueuser and ngroup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_ngroups_for_cueuser(cueuser_id: UUID) -> List[UUID]:
    """Retrieves all ngroups associated with a cueuser."""
    pool: Pool = await get_connection_pool()
    params = (cueuser_id,)
    try:
        return await query(pool, cueuser_ngroup_db.list_ngroups_for_cueuser_from_db, params)
    except Exception as e:
        logger.error(f"Error listing ngroups for cueuser: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_cueusers_in_ngroup(ngroup_id: UUID) -> List[UUID]:
    """Retrieves all cueusers associated with an ngroup."""
    pool: Pool = await get_connection_pool()
    params = (ngroup_id,)
    try:
        return await query(pool, cueuser_ngroup_db.list_cueusers_in_ngroup_from_db, params)
    except Exception as e:
        logger.error(f"Error listing cueusers in ngroup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()