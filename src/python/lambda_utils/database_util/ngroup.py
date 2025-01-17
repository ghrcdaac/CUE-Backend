from asyncpg import Connection
from typing import Tuple, List, Optional
from lambda_utils.type_util.ngroup import NgroupReturn
from uuid import UUID

async def create_ngroup_in_db(conn: Connection, params: Tuple) -> List[NgroupReturn]:
    """Inserts a new ngroup record into the database."""
    insert_query = """
        INSERT INTO ngroup (id, short_name, long_name)
        VALUES ($1, $2, $3)
        RETURNING id, short_name, long_name
    """
    return await conn.fetch(insert_query, *params)

async def get_ngroup_id_from_db(conn: Connection, params: Tuple) -> Optional[UUID]:
    """Retrieves the ngroup ID based on short_name or long_name."""
    select_query = """
        SELECT id
        FROM ngroup
        WHERE short_name = $1 OR long_name = $2
    """
    result = await conn.fetchrow(select_query, *params)
    if result:
        return result['id']  # Access the UUID using the column name 'id'
    else:
        return None

async def get_ngroup_from_db(conn: Connection, params: Tuple) -> List[NgroupReturn]:
    """Retrieves an ngroup record from the database by its ID."""
    select_query = """
        SELECT id, short_name, long_name
        FROM ngroup
        WHERE id = $1
    """
    return await conn.fetch(select_query, *params)

async def update_ngroup_in_db(conn: Connection, params: Tuple) -> List[NgroupReturn]:
    """Updates an existing ngroup record in the database."""
    update_query = """
        UPDATE ngroup
        SET short_name = $2, long_name = $3
        WHERE id = $1
        RETURNING id, short_name, long_name
    """
    return await conn.fetch(update_query, *params)

async def delete_ngroup_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes an ngroup record from the database by its ID."""
    delete_query = """
        DELETE FROM ngroup
        WHERE id = $1
    """
    result = await conn.execute(delete_query, *params)
    return result == "DELETE 1"

async def list_ngroups_from_db(conn: Connection, params: Tuple) -> List[NgroupReturn]: 
    """Retrieves all ngroup records from the database."""
    select_query = """
        SELECT id, short_name, long_name
        FROM ngroup
    """
    return await conn.fetch(select_query)