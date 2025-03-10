from asyncpg import Connection
from typing import Tuple, List, Any, Optional
from uuid import UUID
from lambda_utils.type_util.user_application import UserApplicationReturn
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
    except Exception as e:
        logger.error(f"Error creating user_application: {e}", exc_info=True)
        raise

async def get_user_application_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves a user_application by ID, optionally filtering by ngroup_id."""
    user_application_id = params[0]
    ngroup_id = params[1] if len(params) > 1 else None

    select_query = """
        SELECT id, email, name, applied, username, status, ngroup_id, provider_id, justification, account_type, edpub_id
        FROM user_application
        WHERE id = $1
    """
    query_params: List[Any] = [user_application_id]
    if ngroup_id:
        select_query += " AND ngroup_id = $2"
        query_params.append(ngroup_id)

    try:
        return await conn.fetch(select_query, *query_params) 
    except Exception as e:
        logger.error(f"Error getting user_application: {e}", exc_info=True)
        raise
async def update_user_application_in_db(conn: Connection, params: Tuple) -> List:
    """Updates an existing user_application record in the database."""
    update_fields, user_application_id = params
    set_clause_parts = []
    values:List[Any] = []

    for i, (field, value) in enumerate(update_fields.items()):
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

    except Exception as e:
        logger.error(f"An unexpected error occurred while updating user application: {e}", exc_info=True)
        raise

async def delete_user_application_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes by ID, optionally filtering by ngroup_id."""
    user_application_id = params[0]
    ngroup_id = params[1] if len(params) > 1 else None

    delete_query = """
        DELETE FROM user_application
        WHERE id = $1
    """
    query_params: List[Any] = [user_application_id]
    if ngroup_id:
        delete_query += " AND ngroup_id = $2"
        query_params.append(ngroup_id)

    try:
        result = await conn.execute(delete_query, *query_params)  
        return result.startswith("DELETE")
    except Exception as e:
        logger.error(f"Error deleting user_application: {e}", exc_info=True)
        raise

async def list_user_applications_from_db(conn: Connection, params: Optional[Tuple]) -> List:
    """Retrieves user_applications, optionally filtering by ngroup_id."""
    select_query = """
        SELECT id, email, name, applied, username, status, ngroup_id, provider_id, justification, account_type, edpub_id
        FROM user_application
    """
    query_params: List[Any] = []
    # ngroup_id is the first and only element, if it exists.
    if params and params[0] is not None: # Safely check if params exists and ngroup exists
        select_query += " WHERE ngroup_id = $1"
        query_params.append(params[0])

    try:
        return await conn.fetch(select_query, *query_params)  
    except Exception as e:
        logger.error(f"Error listing user_applications: {e}", exc_info=True)
        raise