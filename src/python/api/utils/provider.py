# utils/provider.py
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import provider as provider_db
from lambda_utils.type_util.provider import ProviderCreate, ProviderReturn, ProviderUpdate
from typing import List, Optional, Any, Tuple
from uuid import UUID
import logging

from utils.cueuser import get_cueuser, CueuserNotFoundError  # For user validation
from utils.ngroup import get_ngroup, NgroupNotFoundError

logger = logging.getLogger(__name__)

class ProviderNotFoundError(Exception):
    def __init__(self, provider_id: UUID = None, short_name: str = None, long_name: str = None, ngroup_id: Optional[UUID]=None):
        if provider_id:
            message = f"Provider not found with ID: {provider_id}"
            if ngroup_id:
                message+=f" and ngroup_id: {ngroup_id}"
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
        self.ngroup = ngroup_id

async def create_provider(provider: ProviderCreate) -> ProviderReturn:
    """Creates a new provider record."""
    pool: Pool = await get_connection_pool()

    # 1. Validate ngroup and cueuser existence *before* creating
    try:
        await get_ngroup(provider.ngroup_id)  # Check ngroup exists
        # Check that the user exists *and* belongs to the correct ngroup
        await get_cueuser(provider.point_of_contact, provider.ngroup_id) # Corrected attribute
    except NgroupNotFoundError:
        raise ValueError(f"Ngroup with ID '{provider.ngroup_id}' not found")
    except CueuserNotFoundError:
        raise ValueError(f"CueUser with ID '{provider.point_of_contact}' not found or is not in the correct ngroup.") # Corrected attribute


    params = (
        provider.ngroup_id,
        provider.short_name,
        provider.long_name,

        provider.can_upload,
        provider.point_of_contact,  # Corrected attribute
        provider.reason,
    )
    try:
        async with pool.acquire() as conn:  # Use a connection explicitly
            async with conn.transaction():  # Use a transaction!
                result = await provider_db.create_provider_in_db(conn, params)
                if not result:
                    raise Exception("Failed to create provider in database.")
                return ProviderReturn.from_db_row(result[0])  # Correctly unpack result


    except Exception as e:
        # No need for explicit rollback; transaction handles it.
        logger.error(f"Error creating provider: {e}", exc_info=True)
        raise  # Re-raise the exception after logging
    finally:
        await pool.close()


async def get_provider(provider_id: UUID, ngroup_id: Optional[UUID] = None) -> ProviderReturn | None:
    """Retrieves a provider record by its ID, optionally filtering by ngroup ID."""
    pool: Pool = await get_connection_pool()
    try:
        params = (provider_id,)
        if ngroup_id:
            params = (provider_id, ngroup_id)
            result = await query(pool, provider_db.get_provider_from_db_ngroup, params, row_mapper=ProviderReturn.from_db_row)
        else:
            result = await query(pool, provider_db.get_provider_from_db, params, row_mapper=ProviderReturn.from_db_row)
        if result:
            return result[0]
        else:
            if ngroup_id:
                raise ProviderNotFoundError(provider_id=provider_id, ngroup_id=ngroup_id)
            raise ProviderNotFoundError(provider_id=provider_id)
    except Exception as e:
        logger.error(f"Error getting provider: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_provider_by_lookup(
    short_name: Optional[str] = None, long_name: Optional[str] = None
) -> ProviderReturn | None:
    """Retrieves a provider record by short_name or long_name (no ngroup filtering on lookup)."""
    if not short_name and not long_name:
        raise ValueError("Either short_name or long_name must be provided")

    pool: Pool = await get_connection_pool()
    if short_name:
        params = (short_name,)
        query_func = provider_db.get_provider_by_short_name_from_db
    else:  # long_name must be provided
        params = (long_name,)
        query_func = provider_db.get_provider_by_long_name_from_db

    try:
        result = await query(pool, query_func, params, row_mapper=ProviderReturn.from_db_row)
        if result:
            return result[0]
        else:
            if short_name:
                raise ProviderNotFoundError(short_name=short_name)
            else:
                 raise ProviderNotFoundError(long_name=long_name)

    except Exception as e:
        logger.error(f"Error during provider lookup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def update_provider(provider_id: UUID, provider_update: ProviderUpdate) -> ProviderReturn | None:
    """Updates an existing provider record, validating point_of_contact."""
    pool: Pool = await get_connection_pool()

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():  # Use a transaction

                # 1. Get the *current* provider data.
                current_provider_rows = await provider_db.get_provider_from_db(conn, (provider_id,))
                if not current_provider_rows:
                    raise ProviderNotFoundError(provider_id=provider_id)
                current_provider = ProviderReturn.from_db_row(current_provider_rows[0])

                # 2. Check if point_of_contact is being updated, and validate the new user.
                new_user_id = provider_update.point_of_contact
                if new_user_id and new_user_id != current_provider.point_of_contact:
                    # Check if the new user exists and belongs to ngroup.
                    try:
                        await get_cueuser(new_user_id, current_provider.ngroup_id) # Corrected attribute
                    except CueuserNotFoundError:
                        raise ValueError(f"CueUser with ID '{new_user_id}' not found or not in the same ngroup.")

                 # 3. Update the provider record itself (including point_of_contact_user_id).
                update_fields = {
                    k: v
                    for k, v in provider_update.model_dump().items()
                    if v is not None
                }

                if update_fields:
                    update_params = (update_fields, provider_id)
                    updated_provider_rows = await provider_db.update_provider_in_db(conn, update_params)
                    if not updated_provider_rows:
                        raise ProviderNotFoundError(provider_id=provider_id) # Should not happen
                    return  ProviderReturn.from_db_row(updated_provider_rows[0]) # Return updated provider
                else:
                     #No updates, return current value.
                    return current_provider

    except Exception as e:
        # Rollback is automatic because of the transaction
        raise
    finally:
        await pool.close()

async def delete_provider(provider_id: UUID, ngroup_id: Optional[UUID] = None) -> bool:
    """Deletes a provider record by its ID, optionally filtered by ngroup_id."""
    pool: Pool = await get_connection_pool()
    params = (provider_id,)
    if ngroup_id:
        params = (provider_id, ngroup_id)
    try:
        result = await query(
            pool,
            provider_db.delete_provider_from_db_ngroup if ngroup_id else provider_db.delete_provider_from_db,
            params
        )
        if not result:
            if ngroup_id:
                raise ProviderNotFoundError(provider_id=provider_id, ngroup_id=ngroup_id)
            raise ProviderNotFoundError(provider_id=provider_id)
        return result
    except Exception as e:
        raise
    finally:
        await pool.close()

async def list_providers(ngroup_id: Optional[UUID] = None, can_upload: Optional[bool] = None) -> List[ProviderReturn]:
    """Retrieves all provider records, optionally filtering by ngroup_id and can_upload."""
    pool: Pool = await get_connection_pool()
    params: List[Any] = []

    if ngroup_id and can_upload is not None:  # Both filters
        query_func = provider_db.list_providers_from_db_ngroup_and_upload
        params = [ngroup_id, can_upload]
    elif ngroup_id:  # Only ngroup_id
        query_func = provider_db.list_providers_from_db_ngroup
        params = [ngroup_id]
    elif can_upload is not None:  # Only can_upload
        query_func = provider_db.list_providers_from_db_upload
        params = [can_upload]
    else:  # No filters
        query_func = provider_db.list_providers_from_db
        params = []

    try:
        results = await query(pool, query_func, tuple(params), row_mapper=ProviderReturn.from_db_row)
        return results
    except Exception as e:
        raise ValueError(f"Failed to list providers: {e}")
    finally:
        await pool.close()