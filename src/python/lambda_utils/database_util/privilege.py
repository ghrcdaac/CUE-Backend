from asyncpg import Connection, UniqueViolationError, DataError
from typing import Tuple, List, Optional

from lambda_utils.type_util.privilege import PrivilegeReturn
import logging

logger = logging.getLogger(__name__)

async def create_privilege_in_db(conn: Connection, params: Tuple) -> List[PrivilegeReturn]:
    """Inserts a new privilege record into the database."""
    insert_query = """
        INSERT INTO privilege (privilege)
        VALUES ($1)
        RETURNING privilege
    """
    try:
        return await conn.fetch(insert_query, *params)
    except UniqueViolationError as e:
        logger.error(f"Failed to create privilege due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A privilege with the given name already exists.")
    except DataError as e:
        logger.error(f"Failed to create privilege due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating a privilege.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating a privilege: {e}", exc_info=True)
        raise

async def get_privilege_from_db(conn: Connection, params: Tuple) -> List[PrivilegeReturn]:
    """Retrieves a privilege record from the database by its name."""
    select_query = """
        SELECT privilege
        FROM privilege
        WHERE privilege = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting a privilege: {e}", exc_info=True)
        raise

async def update_privilege_in_db(conn: Connection, params: Tuple) -> List[PrivilegeReturn]:
    """Updates an existing privilege record in the database."""
    update_query = """
        UPDATE privilege
        SET privilege = $2
        WHERE privilege = $1
        RETURNING privilege
    """
    try:
        return await conn.fetch(update_query, *params)
    except UniqueViolationError as e:
        logger.error(f"Failed to update privilege due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A privilege with the given name already exists.")
    except DataError as e:
        logger.error(f"Failed to update privilege due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for updating a privilege.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating a privilege: {e}", exc_info=True)
        raise

async def delete_privilege_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes a privilege record from the database by its name."""
    delete_query = """
        DELETE FROM privilege
        WHERE privilege = $1
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting a privilege: {e}", exc_info=True)
        raise

async def list_privileges_from_db(conn: Connection) -> List[PrivilegeReturn]:
    """Retrieves all privilege records from the database."""
    select_query = """
        SELECT privilege
        FROM privilege
    """
    try:
        return await conn.fetch(select_query)
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing privileges: {e}", exc_info=True)
        raise

async def get_privilege_by_lookup_from_db(conn: Connection, params: Tuple) -> List[PrivilegeReturn]:
    """Retrieves a privilege record from the database by name."""
    select_query = """
        SELECT privilege
        FROM privilege
        WHERE privilege = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred during privilege lookup: {e}", exc_info=True)
        raise