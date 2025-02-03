from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError, DataError
from typing import Tuple, List
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

async def create_cueuser_provider_association_in_db(conn: Connection, params: Tuple) -> bool:
    """Associates a cueuser with a provider in the database."""
    insert_query = """
        INSERT INTO cueuser_provider (cueuser_id, provider_id)
        VALUES ($1, $2)
    """
    try:
        await conn.execute(insert_query, *params)
        return True
    except UniqueViolationError as e:
        logger.error(f"Failed to create association due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("The cueuser is already associated with the provider.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to create association due to foreign key violation: {e}", exc_info=True)
        raise ValueError("Invalid cueuser_id or provider_id provided.")
    except DataError as e:
        logger.error(f"Failed to create association due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating association.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating association: {e}", exc_info=True)
        raise

async def delete_cueuser_provider_association_from_db(conn: Connection, params: Tuple) -> bool:
    """Removes the association between a cueuser and a provider in the database."""
    delete_query = """
        DELETE FROM cueuser_provider
        WHERE cueuser_id = $1 AND provider_id = $2
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting association: {e}", exc_info=True)
        raise

async def list_providers_for_cueuser_from_db(conn: Connection, params: Tuple) -> List[UUID]:
    """Retrieves all provider IDs associated with a cueuser from the database."""
    select_query = """
        SELECT provider_id
        FROM cueuser_provider
        WHERE cueuser_id = $1
    """
    try:
        results = await conn.fetch(select_query, *params)
        return [result['provider_id'] for result in results]
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing providers for cueuser: {e}", exc_info=True)
        raise

async def list_cueusers_for_provider_from_db(conn: Connection, params: Tuple) -> List[UUID]:
    """Retrieves all cueuser IDs associated with a provider from the database."""
    select_query = """
        SELECT cueuser_id
        FROM cueuser_provider
        WHERE provider_id = $1
    """
    try:
        results = await conn.fetch(select_query, *params)
        return [result['cueuser_id'] for result in results]
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing cueusers for provider: {e}", exc_info=True)
        raise