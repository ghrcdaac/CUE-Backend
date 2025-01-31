from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import provider as provider_db
from lambda_utils.type_util.provider import ProviderCreate, ProviderReturn, ProviderUpdate
from typing import List, Optional
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class ProviderNotFoundError(Exception):
    def __init__(self, provider_id: UUID = None, short_name: str = None, long_name: str = None):
        if provider_id:
            message = f"Provider not found with ID: {provider_id}"
        elif short_name:
            message = f"Provider not found with short_name: {short_name}"
        elif long_name:
            message = f"Provider not found with long_name: {long_name}"
        else:
            message = "Provider not found"
        super().__init__(message)
        self.provider_id = provider_id
        self.short_name = short_name
        self.long_name = long_name

async def create_provider(provider: ProviderCreate) -> ProviderReturn:
    """Creates a new provider record."""
    pool: Pool = await get_connection_pool()
    params = (provider.ngroup_id, provider.short_name, provider.long_name, provider.can_upload, provider.point_of_contact_user_id)
    try:
        result = await query(pool, provider_db.create_provider_in_db, params, row_mapper=ProviderReturn.from_db_row)
        return result[0]
    except Exception as e:
        logger.error(f"Error creating provider: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_provider(provider_id: UUID) -> ProviderReturn | None:
    """Retrieves a provider record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (provider_id,)
    try:
        result = await query(pool, provider_db.get_provider_from_db, params, row_mapper=ProviderReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise ProviderNotFoundError(provider_id=provider_id)
    except Exception as e:
        logger.error(f"Error getting provider: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_provider_by_lookup(
    short_name: Optional[str] = None,
    long_name: Optional[str] = None
) -> ProviderReturn | None:
    """Retrieves a provider record by short_name or long_name."""
    if not short_name and not long_name:
        raise ValueError("Either short_name or long_name must be provided")

    pool: Pool = await get_connection_pool()
    params = (short_name, long_name)
    try:
        result = await query(pool, provider_db.get_provider_by_lookup_from_db, params, row_mapper=ProviderReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise ProviderNotFoundError(short_name=short_name, long_name=long_name)
    except Exception as e:
        logger.error(f"Error during provider lookup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def update_provider(provider_id: UUID, provider_update: ProviderUpdate) -> ProviderReturn | None:
    """Updates an existing provider record."""
    pool: Pool = await get_connection_pool()
    update_fields = {k: v for k, v in provider_update.model_dump().items() if v is not None}
    if not update_fields:
        return await get_provider(provider_id)

    params = (update_fields, provider_id)
    try:
        result = await query(pool, provider_db.update_provider_in_db, params, row_mapper=ProviderReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise ProviderNotFoundError(provider_id=provider_id)
    except Exception as e:
        logger.error(f"Error updating provider: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def delete_provider(provider_id: UUID) -> bool:
    """Deletes a provider record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (provider_id,)
    try:
        result = await query(pool, provider_db.delete_provider_from_db, params)
        if not result:
            raise ProviderNotFoundError(provider_id=provider_id)
        return result
    except Exception as e:
        logger.error(f"Error deleting provider: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_providers(
    ngroup_id: Optional[UUID] = None,
    can_upload: Optional[bool] = None
) -> List[ProviderReturn]:
    """Retrieves all provider records with optional filters."""
    pool: Pool = await get_connection_pool()
    try:
        results = await query(pool, provider_db.list_providers_from_db, (ngroup_id, can_upload), row_mapper=ProviderReturn.from_db_row)
        return results
    except Exception as e:
        logger.error(f"Error listing providers: {e}", exc_info=True)
        raise
    finally:
        await pool.close()