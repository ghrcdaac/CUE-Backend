from asyncpg import Connection, UniqueViolationError, DataError, ForeignKeyViolationError
from typing import Tuple, List, Optional, Any 
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
        logger.error(f"Failed to create provider: {e}", exc_info=True)
        raise ValueError("Unique constraint violation.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to create provider: {e}", exc_info=True)
        raise ValueError("Foreign key violation.")
    except DataError as e:
        logger.error(f"Failed to create provider: {e}", exc_info=True)
        raise ValueError("Invalid data.")
    except Exception as e:
        logger.error(f"Error creating provider: {e}", exc_info=True)
        raise

async def get_provider_from_db(conn: Connection, params: Tuple) -> List[ProviderReturn]:
    """Retrieves a provider by ID, optionally filtering by ngroup_id."""
    provider_id = params[0]  
    ngroup_id = params[1] if len(params) > 1 else None

    select_query = """
        SELECT id, ngroup_id, short_name, long_name, can_upload, point_of_contact
        FROM provider
        WHERE id = $1
    """
    query_params: List[Any] = [provider_id]  

    if ngroup_id:
        select_query += " AND ngroup_id = $2"
        query_params.append(ngroup_id)

    try:
        return await conn.fetch(select_query, *query_params)  
    except Exception as e:
        logger.error(f"Error getting provider: {e}", exc_info=True)
        raise

async def get_provider_by_lookup_from_db(conn: Connection, params: Tuple) -> List[ProviderReturn]:
    """Retrieves a provider by short_name or long_name."""
    select_query = """
        SELECT id, ngroup_id, short_name, long_name, can_upload, point_of_contact
        FROM provider
        WHERE short_name = $1 OR long_name = $2
    """
    try:
        return await conn.fetch(select_query, *params)  
    except Exception as e:
        logger.error(f"Error during provider lookup: {e}", exc_info=True)
        raise

async def update_provider_in_db(conn: Connection, params: Tuple) -> List[ProviderReturn]:
    """Updates an existing provider."""
    update_fields, provider_id = params
    set_clause_parts = []
    values: List[Any] = []  

    for i, (field, value) in enumerate(update_fields.items()):
        set_clause_parts.append(f"{field} = ${i + 1}")
        values.append(value)

    values.append(provider_id)
    set_clause = ", ".join(set_clause_parts)
    update_query = f"""
        UPDATE provider SET {set_clause}
        WHERE id = ${len(values)}
        RETURNING id, ngroup_id, short_name, long_name, can_upload, point_of_contact
    """
    try:
        return await conn.fetch(update_query, *values)  
    except Exception as e:
        logger.error(f"Error updating provider: {e}", exc_info=True)
        raise

async def delete_provider_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes a provider by ID, optionally filtering by ngroup_id."""
    provider_id = params[0]
    ngroup_id = params[1] if len(params) > 1 else None

    delete_query = """
        DELETE FROM provider
        WHERE id = $1
    """
    query_params: List[Any] = [provider_id]
    if ngroup_id:
        delete_query += " AND ngroup_id = $2"
        query_params.append(ngroup_id)

    try:
        result = await conn.execute(delete_query, *query_params)  
        return result.startswith("DELETE")
    except Exception as e:
        logger.error(f"Error deleting provider: {e}", exc_info=True)
        raise

async def list_providers_from_db(conn: Connection, params: Tuple) -> List[ProviderReturn]:
    """Lists providers, filtering by ngroup_id and can_upload."""
    ngroup_id, can_upload = params[0], params[1] if len(params) > 1 else None  
    query_parts = ["SELECT id, ngroup_id, short_name, long_name, can_upload, point_of_contact FROM provider"]
    where_parts = []
    query_params: List[Any] = []

    if ngroup_id:
        where_parts.append("ngroup_id = $1")
        query_params.append(ngroup_id)
    if can_upload is not None:
        where_parts.append(f"can_upload = ${len(query_params) + 1}")
        query_params.append(can_upload)

    if where_parts:
        query_parts.append("WHERE")
        query_parts.append(" AND ".join(where_parts))

    select_query = " ".join(query_parts)
    logger.info(f"Listing providers with query: {select_query} and params: {query_params}")

    try:
        return await conn.fetch(select_query, *query_params)  
    except Exception as e:
        logger.error(f"Error listing providers: {e}", exc_info=True)
        raise