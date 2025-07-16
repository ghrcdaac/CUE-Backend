from asyncpg import Connection, UniqueViolationError, DataError
from typing import Tuple, List, Optional
from uuid import UUID

from lambda_utils.type_util.role import RoleReturn
import logging

logger = logging.getLogger(__name__)

async def create_role_in_db(conn: Connection, params: Tuple) -> List[RoleReturn]:
    """Inserts a new role record into the database."""
    insert_query = """
        INSERT INTO role (short_name, long_name)
        VALUES ($1, $2)
        RETURNING id, short_name, long_name
    """
    try:
        return await conn.fetch(insert_query, *params)
    except UniqueViolationError as e:
        logger.error(f"Failed to create role due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A role with the given short_name or long_name already exists.")
    except DataError as e:
        logger.error(f"Failed to create role due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating a role.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating a role: {e}", exc_info=True)
        raise

async def get_role_from_db(conn: Connection, params: Tuple) -> List[RoleReturn]:
    """Retrieves a role record from the database by its ID."""
    select_query = """
        SELECT id, short_name, long_name
        FROM role
        WHERE id = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting a role: {e}", exc_info=True)
        raise

async def update_role_in_db(conn: Connection, params: Tuple) -> List[RoleReturn]:
    """Updates an existing role record in the database."""
    update_fields, role_id = params
    set_clause = ", ".join([f"{field} = ${i+1}" for i, field in enumerate(update_fields.keys())])
    values = list(update_fields.values())
    values.append(role_id)

    update_query = f"""
        UPDATE role
        SET {set_clause}
        WHERE id = ${len(values)}
        RETURNING id, short_name, long_name
    """
    try:
        return await conn.fetch(update_query, *values)
    except UniqueViolationError as e:
        logger.error(f"Failed to update role due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A role with the given short_name or long_name already exists.")
    except DataError as e:
        logger.error(f"Failed to update role due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for updating a role.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating a role: {e}", exc_info=True)
        raise

async def delete_role_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes a role record from the database by its ID."""
    delete_query = """
        DELETE FROM role
        WHERE id = $1
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting a role: {e}", exc_info=True)
        raise

async def list_roles_from_db(conn: Connection) -> List[RoleReturn]:
    """Retrieves all role records from the database."""
    select_query = """
        SELECT id, short_name, long_name
        FROM role
    """
    try:
        return await conn.fetch(select_query)
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing roles: {e}", exc_info=True)
        raise

async def get_role_by_lookup_from_db(conn: Connection, params: Tuple) -> List[RoleReturn]:
    """Retrieves a role record from the database by short_name or long_name."""
    select_query = """
        SELECT id, short_name, long_name
        FROM role
        WHERE short_name = $1 OR long_name = $2
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred during role lookup: {e}", exc_info=True)
        raise