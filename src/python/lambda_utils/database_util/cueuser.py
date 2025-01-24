from asyncpg import Connection, UniqueViolationError, DataError
from typing import Tuple, List, Optional
from uuid import UUID
from datetime import datetime

from lambda_utils.type_util.cueuser import CueuserReturn
import logging

logger = logging.getLogger(__name__)

async def create_cueuser_in_db(conn: Connection, params: Tuple) -> List[CueuserReturn]:
    """Inserts a new cueuser record into the database."""
    insert_query = """
        INSERT INTO cueuser (email, name, cueusername, edpub_id)
        VALUES ($1, $2, $3, $4)
        RETURNING id, email, name, registered, cueusername, edpub_id
    """
    try:
        return await conn.fetch(insert_query, *params)
    except UniqueViolationError as e:
        logger.error(f"Failed to create cueuser due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A cueuser with the given email or username already exists.")
    except DataError as e:
        logger.error(f"Failed to create cueuser due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating a cueuser.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating a cueuser: {e}", exc_info=True)
        raise

async def get_cueuser_from_db(conn: Connection, params: Tuple) -> List[CueuserReturn]:
    """Retrieves a cueuser record from the database by its ID."""
    select_query = """
        SELECT id, email, name, registered, cueusername, edpub_id
        FROM cueuser
        WHERE id = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting a cueuser: {e}", exc_info=True)
        raise

async def update_cueuser_in_db(conn: Connection, params: Tuple) -> List[CueuserReturn]:
    """Updates an existing cueuser record in the database."""
    update_fields, cueuser_id = params
    set_clause = ", ".join([f"{field} = ${i+1}" for i, field in enumerate(update_fields.keys())])
    values = list(update_fields.values())
    values.append(cueuser_id)

    update_query = f"""
        UPDATE cueuser
        SET {set_clause}
        WHERE id = ${len(values)}
        RETURNING id, email, name, registered, cueusername, edpub_id
    """
    try:
        return await conn.fetch(update_query, *values)
    except UniqueViolationError as e:
        logger.error(f"Failed to update cueuser due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A cueuser with the given email or username already exists.")
    except DataError as e:
        logger.error(f"Failed to update cueuser due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for updating a cueuser.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating a cueuser: {e}", exc_info=True)
        raise

async def delete_cueuser_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes a cueuser record from the database by its ID."""
    delete_query = """
        DELETE FROM cueuser
        WHERE id = $1
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting a cueuser: {e}", exc_info=True)
        raise

async def list_cueusers_from_db(conn: Connection) -> List[CueuserReturn]:
    """Retrieves all cueuser records from the database."""
    select_query = """
        SELECT id, email, name, registered, cueusername, edpub_id
        FROM cueuser
    """
    try:
        return await conn.fetch(select_query)
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing cueusers: {e}", exc_info=True)
        raise

async def get_cueuser_by_lookup_from_db(conn: Connection, params: Tuple) -> List[CueuserReturn]:
    """Retrieves a cueuser record from the database by email, username, name, or edpub_id."""
    select_query = """
        SELECT id, email, name, registered, cueusername, edpub_id
        FROM cueuser
        WHERE email = $1 OR cueusername = $2 OR name = $3 OR edpub_id = $4
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred during cueuser lookup: {e}", exc_info=True)
        raise