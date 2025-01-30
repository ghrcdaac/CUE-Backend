from asyncpg import Connection, UniqueViolationError, DataError, ForeignKeyViolationError
from typing import Tuple, List, Optional
from uuid import UUID

from lambda_utils.type_util.provider import ProviderReturn
import logging

logger = logging.getLogger(__name__)

async def create_provider_in_db(conn: Connection, params: Tuple) -> List[ProviderReturn]:
    """Inserts a new provider record into the database."""
    insert_query = """
        INSERT INTO provider (ngroup_id, short_name, long_name, can_upload, point_of_contact)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, ngroup_id, short_name, long_name, can_upload, point_of_contact
    """
    try:
        return await conn.fetch(insert_query, *params)
    except UniqueViolationError as e:
        logger.error(f"Failed to create provider due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A provider with the given short_name or long_name already exists.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to create provider due to foreign key violation: {e}", exc_info=True)
        raise ValueError("Invalid ngroup_id or point_of_contact_user_id provided.")
    except DataError as e:
        logger.error(f"Failed to create provider due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating a provider.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating a provider: {e}", exc_info=True)
        raise

async def get_provider_from_db(conn: Connection, params: Tuple) -> List[ProviderReturn]:
    """Retrieves a provider record from the database by its ID."""
    select_query = """
        SELECT id, ngroup_id, short_name, long_name, can_upload, point_of_contact
        FROM provider
        WHERE id = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting a provider: {e}", exc_info=True)
        raise

async def get_provider_by_lookup_from_db(conn: Connection, params: Tuple) -> List[ProviderReturn]:
    """Retrieves a provider record from the database by short_name or long_name."""
    select_query = """
        SELECT id, ngroup_id, short_name, long_name, can_upload, point_of_contact
        FROM provider
        WHERE short_name = $1 OR long_name = $2
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred during provider lookup: {e}", exc_info=True)
        raise

async def update_provider_in_db(conn: Connection, params: Tuple) -> List[ProviderReturn]:
    """Updates an existing provider record in the database."""
    update_fields, provider_id = params
    set_clause_parts = []
    values = []

    for i, (field, value) in enumerate(update_fields.items()):
        set_clause_parts.append(f"{field} = ${i + 1}")
        values.append(value)

    values.append(provider_id)
    set_clause = ", ".join(set_clause_parts)

    update_query = f"""
        UPDATE provider
        SET {set_clause}
        WHERE id = ${len(values)}
        RETURNING id, ngroup_id, short_name, long_name, can_upload, point_of_contact
    """
    try:
        return await conn.fetch(update_query, *values)
    except UniqueViolationError as e:
        logger.error(f"Failed to update provider due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A provider with the given short_name or long_name already exists.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to update provider due to foreign key violation: {e}", exc_info=True)
        raise ValueError("Invalid ngroup_id or point_of_contact_user_id provided.")
    except DataError as e:
        logger.error(f"Failed to update provider due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for updating a provider.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating a provider: {e}", exc_info=True)
        raise

async def delete_provider_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes a provider record from the database by its ID."""
    delete_query = """
        DELETE FROM provider
        WHERE id = $1
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting a provider: {e}", exc_info=True)
        raise

async def list_providers_from_db(conn: Connection, params: Tuple) -> List[ProviderReturn]:
    """Retrieves all provider records from the database."""
    ngroup_id, can_upload = params
    
    query_parts = ["SELECT id, ngroup_id, short_name, long_name, can_upload, point_of_contact FROM provider"]
    where_parts = []
    query_params = []

    if ngroup_id:
        where_parts.append("ngroup_id = $1")
        query_params.append(ngroup_id)
    if can_upload is not None:  # Use 'is not None' for boolean checks
        where_parts.append(f"can_upload = ${2 if ngroup_id else 1}")
        query_params.append(can_upload)

    if where_parts:
        query_parts.append("WHERE")
        query_parts.append(" AND ".join(where_parts))

    select_query = " ".join(query_parts)
    logger.info(f"Listing providers with query: {select_query} and params: {params}")

    try:
        return await conn.fetch(select_query, *query_params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing providers: {e}", exc_info=True)
        raise