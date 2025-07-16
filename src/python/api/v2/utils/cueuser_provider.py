from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import cueuser_provider as cueuser_provider_db
from lambda_utils.type_util.cueuser_provider import CueuserProviderCreate, CueuserProviderReturn
from typing import List
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class CueuserProviderAssociationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)

class CueuserProviderNotFoundError(Exception):
    def __init__(self, cueuser_id: UUID, provider_id: UUID):
        super().__init__(f"Association between Cueuser ID: {cueuser_id} and Provider ID: {provider_id} not found")
        self.cueuser_id = cueuser_id
        self.provider_id = provider_id

async def create_cueuser_provider_association(data: CueuserProviderCreate) -> bool:
    """Associates a cueuser with a provider."""
    pool: Pool = await get_connection_pool()
    params = (data.cueuser_id, data.provider_id)
    try:
        result = await query(pool, cueuser_provider_db.create_cueuser_provider_association_in_db, params)
        return result
    except ValueError as e:
        logger.error(f"Error associating cueuser with provider: {e}", exc_info=True)
        raise CueuserProviderAssociationError(str(e))
    finally:
        await pool.close()

async def delete_cueuser_provider_association(data: CueuserProviderCreate) -> bool:
    """Removes the association between a cueuser and a provider."""
    pool: Pool = await get_connection_pool()
    params = (data.cueuser_id, data.provider_id)
    try:
        result = await query(pool, cueuser_provider_db.delete_cueuser_provider_association_from_db, params)
        if not result:
            raise CueuserProviderNotFoundError(data.cueuser_id, data.provider_id)
        return result
    except Exception as e:
        logger.error(f"Error removing association between cueuser and provider: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_providers_for_cueuser(cueuser_id: UUID) -> List[UUID]:
    """Retrieves all provider IDs associated with a cueuser."""
    pool: Pool = await get_connection_pool()
    params = (cueuser_id,)
    try:
        return await query(pool, cueuser_provider_db.list_providers_for_cueuser_from_db, params)
    except Exception as e:
        logger.error(f"Error listing providers for cueuser: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_cueusers_for_provider(provider_id: UUID) -> List[UUID]:
    """Retrieves all cueuser IDs associated with a provider."""
    pool: Pool = await get_connection_pool()
    params = (provider_id,)
    try:
        return await query(pool, cueuser_provider_db.list_cueusers_for_provider_from_db, params)
    except Exception as e:
        logger.error(f"Error listing cueusers for provider: {e}", exc_info=True)
        raise
    finally:
        await pool.close()