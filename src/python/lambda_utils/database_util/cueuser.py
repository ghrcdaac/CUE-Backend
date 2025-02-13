from asyncpg import Connection, UniqueViolationError, DataError, ForeignKeyViolationError
from typing import Tuple, List, Optional
from uuid import UUID
from datetime import datetime

# Corrected import
from lambda_utils.type_util.cueuser import CueuserReturn, CueuserAuth
import logging

logger = logging.getLogger(__name__)

async def create_cueuser_in_db(conn: Connection, params: Tuple) -> List[CueuserReturn]:
    """Inserts a new cueuser record into the database."""
    insert_query = """
        INSERT INTO cueuser (id, email, name, registered, cueusername, edpub_id)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, email, name, registered, cueusername, edpub_id
    """
    try:
        return await conn.fetch(insert_query, *params)
    except UniqueViolationError as e:
        logger.error(f"Failed to create cueuser due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A cueuser with the given email or username already exists.") from e
    except DataError as e:
        logger.error(f"Failed to create cueuser due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating a cueuser.") from e
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
        raise ValueError("A cueuser with the given email or username already exists.") from e
    except DataError as e:
        logger.error(f"Failed to update cueuser due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for updating a cueuser.") from e
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

async def get_cueuser_by_username(conn: Connection, params: Tuple) -> List[CueuserAuth]:
    """Retrieves a cueuser record from the database by username, including ngroup and role."""
    select_query = """
        SELECT
            cueuser.id AS id,
            email,
            name,
            registered,
            cueuser.cueusername AS cueusername,
            edpub_id,
            ng.short_name as ngroup,
            r.short_name as role_name
        FROM cueuser
        LEFT JOIN cueuser_ngroup as cn ON cueuser.id = cn.cueuser_id
        LEFT JOIN ngroup as ng ON cn.ngroup_id = ng.id
        left join cueuser_role as cr on cr.cueuser_id = cueuser.id
        left join role as r on r.id = cr.role_id
        WHERE cueuser.cueusername = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred during cueuser lookup: {e}", exc_info=True)
        raise


async def login_cueuser(conn: Connection, params: Tuple):
    update_query = """
    UPDATE cueuser_auth
    SET last_login = now(),
        refresh_token = $1
    WHERE id = (SELECT id FROM cueuser WHERE cueusername = $2)
    """
    try:
        return await conn.execute(update_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating last login time: {e}", exc_info=True)
        raise