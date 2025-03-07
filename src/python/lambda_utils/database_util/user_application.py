from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError, DataError
from typing import Tuple, List, Optional
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

async def create_user_application_in_db(conn: Connection, params: Tuple) -> List:
    """Inserts a new user_application record into the database."""
    insert_query = """
        INSERT INTO user_application (email, name, applied, username, status, ngroup_id, provider_id, justification, account_type, edpub_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id, email, name, applied, username, status, ngroup_id, provider_id, justification, account_type, edpub_id
    """
    try:
        return await conn.fetch(insert_query, *params)
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to create user_application due to foreign key violation: {e}", exc_info=True)
        raise ValueError("Invalid ngroup_id or provider_id provided.") from e
    except DataError as e:
        logger.error(f"Failed to create user_application due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating a user_application.") from e
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating a user_application: {e}", exc_info=True)
        raise

async def get_user_application_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves a user_application record from the database by its ID."""
    select_query = """
        SELECT id, email, name, applied, username, status, ngroup_id, provider_id, justification, account_type, edpub_id
        FROM user_application
        WHERE id = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting a user_application: {e}", exc_info=True)
        raise

async def update_user_application_in_db(conn: Connection, params: Tuple) -> List:
    """Updates an existing user_application record in the database."""
    update_fields, user_application_id = params
    set_clause_parts = []
    values = []

    for i, (field, value) in enumerate(update_fields.items()):
# No type casting
        set_clause_parts.append(f"{field} = ${i + 1}")
        values.append(value)
    values.append(user_application_id)
    set_clause = ", ".join(set_clause_parts)


    update_query = f"""
        UPDATE user_application
        SET {set_clause}
        WHERE id = ${len(values)}
        RETURNING id, email, name, applied, username, status, ngroup_id, provider_id, justification, account_type, edpub_id
    """
    try:
        return await conn.fetch(update_query, *values)

    except ForeignKeyViolationError as e:
        logger.error(f"Failed to update user_application due to foreign key violation: {e}", exc_info=True)
        raise ValueError("Invalid ngroup_id or provider_id provided.") from e
    except DataError as e:
        logger.error(f"Failed to update user_application due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for updating a user_application.") from e
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating user application: {e}", exc_info=True)
        raise


async def delete_user_application_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes a user_application record from the database by its ID."""
    delete_query = """
        DELETE FROM user_application
        WHERE id = $1
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting a user_application: {e}", exc_info=True)
        raise

async def list_user_applications_from_db(conn: Connection) -> List:
    """Retrieves all user_application records from the database."""
    select_query = """
        SELECT id, email, name, applied, username, status, ngroup_id, provider_id, justification, account_type, edpub_id
        FROM user_application
    """
    try:
        return await conn.fetch(select_query)
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing user_applications: {e}", exc_info=True)
        raise