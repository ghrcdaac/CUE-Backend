from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError, DataError
from typing import Tuple, List
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

async def create_role_privilege_association_in_db(conn: Connection, params: Tuple) -> bool:
    """Associates a role with a privilege in the database."""
    insert_query = """
        INSERT INTO role_privilege (role_id, privilege)
        VALUES ($1, $2)
    """
    try:
        await conn.execute(insert_query, *params)
        return True
    except UniqueViolationError as e:
        logger.error(f"Failed to create association due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("The role is already associated with the privilege.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to create association due to foreign key violation: {e}", exc_info=True)
        raise ValueError("Invalid role_id or privilege provided.")
    except DataError as e:
        logger.error(f"Failed to create association due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating association.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating association: {e}", exc_info=True)
        raise

async def delete_role_privilege_association_from_db(conn: Connection, params: Tuple) -> bool:
    """Removes the association between a role and a privilege in the database."""
    delete_query = """
        DELETE FROM role_privilege
        WHERE role_id = $1 AND privilege = $2
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting association: {e}", exc_info=True)
        raise

async def list_privileges_for_role_from_db(conn: Connection, params: Tuple) -> List[str]:
    """Retrieves all privileges associated with a role from the database."""
    select_query = """
        SELECT privilege
        FROM role_privilege
        WHERE role_id = $1
    """
    try:
        results = await conn.fetch(select_query, *params)
        return [result['privilege'] for result in results]
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing privileges for role: {e}", exc_info=True)
        raise

async def list_roles_with_privilege_from_db(conn: Connection, params: Tuple) -> List[UUID]:
    """Retrieves all roles associated with a privilege from the database."""
    select_query = """
        SELECT role_id
        FROM role_privilege
        WHERE privilege = $1
    """
    try:
        results = await conn.fetch(select_query, *params)
        return [result['role_id'] for result in results]
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing roles with privilege: {e}", exc_info=True)
        raise