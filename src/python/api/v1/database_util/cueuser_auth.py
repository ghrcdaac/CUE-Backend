from asyncpg import Connection, DataError
from typing import Tuple, List
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

async def create_cueuser_auth_in_db(conn: Connection, params: Tuple) -> bool:
    """Inserts a new cueuser_auth record into the database."""
    insert_query = """
        INSERT INTO cueuser_auth (id, refresh_token, last_login)
        VALUES ($1, $2, $3)
    """
    try:
        await conn.execute(insert_query, *params)
        return True
    except Exception as e:
        logger.error(f"Failed to create cueuser_auth record: {e}", exc_info=True)
        return False

async def get_cueuser_auth_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves a cueuser_auth record from the database by its ID."""
    select_query = """
        SELECT id, refresh_token, last_login
        FROM cueuser_auth
        WHERE id = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting a cueuser_auth record: {e}", exc_info=True)
        raise

async def update_cueuser_auth_in_db(conn: Connection, params: Tuple) -> List:
    """Updates an existing cueuser_auth record in the database."""
    update_fields, cueuser_id = params
    set_clause = ", ".join([f"{field} = ${i+1}" for i, field in enumerate(update_fields.keys())])
    values = list(update_fields.values())
    values.append(cueuser_id)

    update_query = f"""
        UPDATE cueuser_auth
        SET {set_clause}
        WHERE id = ${len(values)}
        RETURNING id, refresh_token, last_login
    """
    try:
        return await conn.fetch(update_query, *values)
    except DataError as e:
        logger.error(f"Failed to update cueuser_auth due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for updating a cueuser_auth record.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating a cueuser_auth record: {e}", exc_info=True)
        raise

async def delete_cueuser_auth_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes a cueuser_auth record from the database by its ID."""
    delete_query = """
        DELETE FROM cueuser_auth
        WHERE id = $1
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting a cueuser_auth record: {e}", exc_info=True)
        raise

async def list_cueuser_auths_from_db(conn: Connection) -> List:
    """Retrieves all cueuser_auth records from the database."""
    select_query = """
        SELECT id, refresh_token, last_login
        FROM cueuser_auth
    """
    try:
        return await conn.fetch(select_query)
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing cueuser_auth records: {e}", exc_info=True)
        raise
    
async def get_cueuser_from_auth(conn: Connection, params: Tuple) -> List:
    """Retrieves the cueuser permission info from the DB."""
    select_query = """
        SELECT 
            c.id,
            c.cueusername,
            c.edpub_id,
            cn.ngroup_id,
            cp.provider_id,
            r.short_name as role_short_name,
            array_agg(rp.privilege) as privileges
        FROM
            cueuser c
        LEFT JOIN
            cueuser_ngroup cn ON c.id = cn.cueuser_id
        LEFT JOIN
            cueuser_provider cp ON c.id = cp.cueuser_id
        LEFT JOIN
            cueuser_role cr ON c.id = cr.cueuser_id
        LEFT JOIN
            role as r ON cr.role_id = r.id
        LEFT JOIN
            role_privilege rp ON r.id = rp.role_id
        WHERE c.id = $1
        GROUP BY c.id, c.cueusername, c.edpub_id, cn.ngroup_id, cp.provider_id, r.short_name
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting cueuser ID from auth: {e}", exc_info=True)
        raise