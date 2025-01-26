from asyncpg import Connection, DataError, UniqueViolationError
from typing import Tuple, List, Optional
from lambda_utils.type_util.ngroup import NgroupReturn
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

async def create_ngroup_in_db(conn: Connection, params: Tuple) -> List[NgroupReturn]:
    """Inserts a new ngroup record into the database."""
    insert_query = """
        INSERT INTO ngroup (id, short_name, long_name)
        VALUES ($1, $2, $3)
        RETURNING id, short_name, long_name
    """
    try:
        return await conn.fetch(insert_query, *params)
    except UniqueViolationError as e:
        logger.error(f"Failed to create ngroup due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A ngroup with the same short_name or long_name already exists.")
    except DataError as e:
        logger.error(f"Failed to create ngroup due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating an ngroup.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating an ngroup: {e}", exc_info=True)
        raise

async def get_ngroup_id_from_db(conn: Connection, params: Tuple) -> Optional[UUID]:
    """Retrieves the ngroup ID based on short_name or long_name."""
    select_query = """
        SELECT id
        FROM ngroup
        WHERE short_name = $1 OR long_name = $2
    """
    try:
        result = await conn.fetchrow(select_query, *params)
        if result:
            return result['id']
        else:
            return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting ngroup ID: {e}", exc_info=True)
        raise

async def get_ngroup_from_db(conn: Connection, params: Tuple) -> List[NgroupReturn]:
    """Retrieves an ngroup record from the database by its ID."""
    select_query = """
        SELECT id, short_name, long_name
        FROM ngroup
        WHERE id = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting an ngroup: {e}", exc_info=True)
        raise

async def update_ngroup_in_db(conn: Connection, params: Tuple) -> List[NgroupReturn]:
    """Updates an existing ngroup record in the database."""
    update_query = """
        UPDATE ngroup
        SET short_name = $2, long_name = $3
        WHERE id = $1
        RETURNING id, short_name, long_name
    """
    try:
        return await conn.fetch(update_query, *params)
    except UniqueViolationError as e:
        logger.error(f"Failed to update ngroup due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A ngroup with the same short_name or long_name already exists.")
    except DataError as e:
        logger.error(f"Failed to update ngroup due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for updating an ngroup.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating an ngroup: {e}", exc_info=True)
        raise

async def delete_ngroup_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes an ngroup record from the database by its ID."""
    delete_query = """
        DELETE FROM ngroup
        WHERE id = $1
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting an ngroup: {e}", exc_info=True)
        raise

async def list_ngroups_from_db(conn: Connection) -> List[NgroupReturn]:
    """Retrieves all ngroup records from the database."""
    select_query = """
        SELECT id, short_name, long_name
        FROM ngroup
    """
    try:
        return await conn.fetch(select_query)
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing ngroups: {e}", exc_info=True)
        raise