from uuid import UUID
from asyncpg import Connection

async def validate_clean_file(conn: Connection, file_id: UUID) -> bool:
    query = """SELECT EXISTS(SELECT 1 FROM file_status where id = $1 and status='clean')"""
    result = await conn.fetchval(query, file_id)
    return result 

async def get_collection_id(conn: Connection, file_id: UUID) -> UUID:
    query = """SELECT collection_id from file where id = $1"""
    result = await conn.fetchval(query, file_id)
    return result