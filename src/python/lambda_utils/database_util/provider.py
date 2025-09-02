# lambda_utils/database_util/provider.py (Corrected)
from asyncpg import Connection, UniqueViolationError, DataError, ForeignKeyViolationError
from typing import Tuple, List, Optional, Dict, Any
from uuid import UUID

from lambda_utils.type_util.provider import ProviderReturn
import logging

logger = logging.getLogger(__name__)

async def create_provider_in_db(conn: Connection, params: Tuple) -> List[ProviderReturn]:
    """Inserts a new provider record into the database."""
    insert_query = """
        INSERT INTO provider (ngroup_id, short_name, long_name, can_upload, point_of_contact, reason)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, ngroup_id, short_name, long_name, can_upload, point_of_contact, reason
    """
    try:
        return await conn.fetch(insert_query, *params)
    except UniqueViolationError as e:
        logger.error(f"Failed to create provider(Unique): {e}", exc_info=True)
        raise ValueError("A provider with the given name already exists.")
    except ForeignKeyViolationError:
        logger.error(f"Failed to create provider(FK): {e}", exc_info=True)
        raise ValueError("Invalid ngroup_id or point_of_contact provided.")
    except Exception as e:
        logger.error(f"Failed to create provider(Unexpected): {e}", exc_info=True)
        raise

async def get_provider_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves a provider record from the database by its ID."""
    select_query = """
        SELECT id, ngroup_id, short_name, long_name, can_upload, point_of_contact, reason
        FROM provider
        WHERE id = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"Error getting provider: {e}", exc_info=True)
        raise

async def get_provider_from_db_ngroup(conn: Connection, params: Tuple) -> List:
    """Retrieves a provider record by its ID, filtered by ngroup ID"""
    select_query = """
        SELECT id, ngroup_id, short_name, long_name, can_upload, point_of_contact, reason
        FROM provider
        WHERE id = $1 AND ngroup_id = $2
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"Error getting provider with ngroup: {e}", exc_info=True)
        raise

async def get_provider_by_short_name_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves a provider record from the database by short_name."""
    select_query = """
     SELECT id, ngroup_id, short_name, long_name, can_upload, point_of_contact, reason
        FROM provider
        WHERE short_name = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"Error getting provider by short_name: {e}", exc_info=True)
        raise

async def get_provider_by_long_name_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves a provider record from the database by long_name."""
    select_query = """
        SELECT id, ngroup_id, short_name, long_name, can_upload, point_of_contact, reason
        FROM provider
        WHERE long_name = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"Error getting provider by long_name: {e}", exc_info=True)
        raise
async def update_provider_in_db(conn: Connection, params: Tuple) -> List:
    """Updates an existing provider record in the database."""
    update_fields, provider_id = params
    set_clause_parts = []
    values = []
    for field, value in update_fields.items():
        set_clause_parts.append(f"{field} = ${len(values) + 1}")
        values.append(value)

    values.append(provider_id)  # Add provider_id at the end
    set_clause = ", ".join(set_clause_parts)

    update_query = f"""
        UPDATE provider
        SET {set_clause}
        WHERE id = ${len(values)}
        RETURNING id, ngroup_id, short_name, long_name, can_upload, point_of_contact, reason
    """

    try:
        return await conn.fetch(update_query, *values)
    except UniqueViolationError as e:
        logger.error(f"Failed to update provider(Unique): {e}", exc_info=True)
        raise ValueError("A provider with the given short_name already exists")
    except ForeignKeyViolationError:
        logger.error(f"Failed to update provider(FK): {e}", exc_info=True)
        raise ValueError("Invalid ngroup_id or point_of_contact provided")
    except Exception as e:
         logger.error(f"Failed to update provider (unexpected): {e}", exc_info=True)
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
        logger.error(f"Error deleting provider: {e}", exc_info=True)
        raise

async def delete_provider_from_db_ngroup(conn: Connection, params: Tuple) -> bool:
    """Deletes a provider record by ID, filtered by ngroup_id."""
    delete_query = """
        DELETE FROM provider
        WHERE id = $1 AND ngroup_id = $2
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result.startswith("DELETE")
    except Exception as e:
        logger.error(f"Error deleting provider with ngroup filter: {e}", exc_info=True)
        raise

async def list_providers_from_db(conn: Connection) -> List:
    """Retrieves all provider records from the database."""
    select_query = """
     SELECT id, ngroup_id, short_name, long_name, can_upload, point_of_contact,reason
        FROM provider
    """
    try:
        return await conn.fetch(select_query)
    except Exception as e:
        logger.error(f"Error listing providers: {e}", exc_info=True)
        raise

async def list_providers_from_db_ngroup(conn: Connection, params: Tuple) -> List:
    """Retrieves provider records filtered by ngroup_id."""
    select_query = """
        SELECT id, ngroup_id, short_name, long_name, can_upload, point_of_contact,reason
        FROM provider
        WHERE ngroup_id = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"Error listing providers with ngroup filter: {e}", exc_info=True)
        raise

async def list_providers_from_db_upload(conn: Connection, params: Tuple) -> List:
    """Retrieves provider records filtered by can_upload."""
    select_query = """
        SELECT id, ngroup_id, short_name, long_name, can_upload, point_of_contact,reason
        FROM provider
        WHERE can_upload = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"Error listing providers with can_upload filter: {e}", exc_info=True)
        raise

async def list_providers_from_db_ngroup_and_upload(conn: Connection, params: Tuple) -> List:
    """Retrieves provider records filtered by ngroup_id and can_upload."""
    select_query = """
        SELECT id, ngroup_id, short_name, long_name, can_upload, point_of_contact,reason
        FROM provider
        WHERE ngroup_id = $1 AND can_upload = $2
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"Error listing providers with ngroup and can_upload filters: {e}", exc_info=True)
        raise