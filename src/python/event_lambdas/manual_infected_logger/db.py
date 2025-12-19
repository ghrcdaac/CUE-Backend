from uuid import UUID
from asyncpg import Connection

async def validate_unscanned_file(conn: Connection, file_id: UUID) -> bool:
    query = """SELECT EXISTS(SELECT 1 FROM file_status WHERE id = $1 AND status = 'unscanned')"""
    result = await conn.fetchval(query, file_id)
    return result 