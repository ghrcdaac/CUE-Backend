from asyncpg import Connection, UniqueViolationError, DataError, ForeignKeyViolationError, Pool
from typing import Tuple, List, Optional, Dict
from uuid import UUID
from datetime import datetime

from lambda_utils.type_util.cueuser import CueuserReturn, CueuserRoleReturn
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


async def get_cueuser_from_db(conn: Connection, params: Tuple) -> Optional[List[Dict]]:
    """
    Retrieves a cueuser record by its ID including role information,
    filtered by ngroup_id.
    """
    query = """
        SELECT
            c.id,
            c.email,
            c.name,
            c.cueusername,
            c.edpub_id,
            cn.ngroup_id,
            cp.provider_id,
            cr.role_id,
            r.short_name as role_short_name,
            r.long_name as role_long_name,
            c.registered
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
        WHERE c.id = $1 AND cn.ngroup_id = $2;
    """
    logger.debug(f"Executing get_cueuser_from_db with query: {query} and params: {params}")
    result = await conn.fetch(query, *params)
    logger.debug(f"Result of get_cueuser_from_db: {result}")
    return result

async def list_cueusers_from_db(conn: Connection, params: Tuple) -> List[Dict]:
    """Retrieves all cueuser records, including role information, filtered by ngroup ID."""
    query = """
        SELECT
            c.id,
            c.email,
            c.name,
            c.cueusername,
            c.edpub_id,
            cn.ngroup_id,
            cp.provider_id,
            cr.role_id,
            r.short_name as role_short_name,
            r.long_name as role_long_name,
            c.registered
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
        WHERE
            cn.ngroup_id = $1;
    """
    result = await conn.fetch(query, *params)
    return result

async def get_cueuser_by_lookup_from_db(conn: Connection, params: Tuple) -> Optional[List[Dict]]:
    """Retrieves a cueuser by email, username, name or edpub_id including role information filtered by ngroup."""
    query = """
        SELECT
            c.id,
            c.email,
            c.name,
            c.cueusername,
            c.edpub_id,
            cn.ngroup_id,
            cp.provider_id,
            cr.role_id,
            r.short_name as role_short_name,
            r.long_name as role_long_name,
            c.registered
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
        WHERE
            (c.email = $1 OR c.cueusername = $2 OR c.name = $3 OR c.edpub_id = $4) AND cn.ngroup_id = $5;
    """
    result = await conn.fetch(query, *params)
    return result

async def get_cueuser_by_username(conn: Connection, username: str) -> Optional[Dict]:
    """Retrieves a cueuser by username."""
    query = """
        SELECT id, email, name, cueusername, edpub_id, registered
        FROM cueuser
        WHERE cueusername = $1;
    """
    return await conn.fetchrow(query, username)



async def create_cueuser_ngroup_association_in_db(conn: Connection, cueuser_id: UUID, ngroup_id: UUID) -> None:
    """Creates an association between a cueuser and an ngroup."""
    query = """
        INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
        VALUES ($1, $2)
        ON CONFLICT (cueuser_id, ngroup_id) DO NOTHING;
    """
    await conn.execute(query, cueuser_id, ngroup_id)


async def create_cueuser_provider_association_in_db(conn: Connection, cueuser_id: UUID, provider_id: UUID) -> None:
    """Creates an association between a cueuser and a provider."""
    query = """
        INSERT INTO cueuser_provider (cueuser_id, provider_id)
        VALUES ($1, $2)
        ON CONFLICT (cueuser_id, provider_id) DO NOTHING;
    """
    await conn.execute(query, cueuser_id, provider_id)


async def create_cueuser_role_association_in_db(conn: Connection, cueuser_id: UUID, role_id: UUID) -> None:
    """Creates an association between a cueuser and a role."""
    query = """
        INSERT INTO cueuser_role (cueuser_id, role_id)
        VALUES ($1, $2)
        ON CONFLICT (cueuser_id, role_id) DO NOTHING;
    """
    await conn.execute(query, cueuser_id, role_id)

async def delete_cueuser_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes a cueuser record by its ID."""
    query = """
        DELETE FROM cueuser
        WHERE id = $1
        RETURNING id;
    """
    result = await conn.execute(query, *params)
    return bool(result)

async def delete_cueuser_ngroup_association_in_db(conn: Connection, cueuser_id: UUID, ngroup_id: UUID) -> None:
    """Deletes an association between a cueuser and a group."""
    query = """
        DELETE FROM cueuser_ngroup
        WHERE cueuser_id = $1 AND ngroup_id = $2;
    """
    await conn.execute(query, cueuser_id, ngroup_id)

async def delete_cueuser_provider_association_in_db(conn: Connection, cueuser_id: UUID, provider_id: UUID) -> None:
    """Deletes an association between a cueuser and a provider."""
    query = """
        DELETE FROM cueuser_provider
        WHERE cueuser_id = $1 AND provider_id = $2;
    """
    await conn.execute(query, cueuser_id, provider_id)

async def delete_cueuser_role_association_in_db(conn: Connection, cueuser_id: UUID, role_id: UUID) -> None:
    """Deletes an association between a cueuser and a role."""
    query = """
        DELETE FROM cueuser_role
        WHERE cueuser_id = $1 AND role_id = $2;
    """
    await conn.execute(query, cueuser_id, role_id)

async def get_cueuser_role_from_db(pool, cueuser_id: UUID):
    """Retrieves the role information (ID, short_name, long_name) for a cueuser."""
    query = """
        SELECT
            cr.role_id,
            r.short_name,
            r.long_name
        FROM
            cueuser_role cr
        INNER JOIN
            role r ON cr.role_id = r.id
        WHERE
            cr.cueuser_id = $1;
    """
    async with pool.acquire() as conn:
        result = await conn.fetchrow(query, cueuser_id)
    return result

async def update_cueuser_in_db(conn: Connection, cueuser_id: UUID, update_data: Dict) -> Optional[Dict]:
    """Updates a cueuser record in the database."""
    if not update_data:
        return None

    set_clause_parts = [f"{key} = ${i+1}" for i, key in enumerate(update_data.keys())]
    set_clause = ", ".join(set_clause_parts)
    query = f"""
        UPDATE cueuser
        SET {set_clause}
        WHERE id = ${len(update_data) + 1}
        RETURNING *;
    """
    values = list(update_data.values())
    values.append(cueuser_id)
    logger.debug(f"update_cueuser_in_db query: {query} values:{values}")
    try:
        return await conn.fetchrow(query, *values)
    except Exception as e:
        logger.error(f"Error updating cueuser: {e}", exc_info=True)
        raise

async def update_cueuser_ngroup_association_in_db(conn: Connection, cueuser_id: UUID, ngroup_id: UUID) -> None:
    """Updates the ngroup association.  Deletes existing, then inserts the new one."""
    await conn.execute("DELETE FROM cueuser_ngroup WHERE cueuser_id = $1", cueuser_id)
    await conn.execute("INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id) VALUES ($1, $2) ON CONFLICT (cueuser_id, ngroup_id) DO NOTHING", cueuser_id, ngroup_id)

async def update_cueuser_provider_association_in_db(conn: Connection, cueuser_id: UUID, provider_id: UUID) -> None:
    """Updates the provider association. Deletes existing, then inserts the new one."""
    await conn.execute("DELETE FROM cueuser_provider WHERE cueuser_id = $1", cueuser_id)
    await conn.execute("INSERT INTO cueuser_provider (cueuser_id, provider_id) VALUES ($1, $2) ON CONFLICT (cueuser_id, provider_id) DO NOTHING", cueuser_id, provider_id)

async def update_cueuser_role_association_in_db(conn: Connection, cueuser_id: UUID, role_id: UUID) -> None:
    """Updates the role association. Deletes existing, then inserts the new one."""
    await conn.execute("DELETE FROM cueuser_role WHERE cueuser_id = $1", cueuser_id)
    await conn.execute("INSERT INTO cueuser_role (cueuser_id, role_id) VALUES ($1, $2) ON CONFLICT (cueuser_id, role_id) DO NOTHING", cueuser_id, role_id)