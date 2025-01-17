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