from asyncpg import Connection
from uuid import UUID

async def check_user_application_approved(conn: Connection, user_id: UUID):
    query = """SELECT EXISTS(SELECT 1 FROM user_application WHERE user_id = $1 AND status = 'approved')"""
    result = await conn.fetchval(query, user_id)
    return result 

async def check_pending_user_application_pending(conn: Connection, application_id: UUID):
    query = """SELECT EXISTS(SELECT 1 FROM user_application WHERE id = $1 AND status = 'pending')"""
    result = await conn.fetchval(query, application_id)
    return result 

async def check_infected_file_exists(conn: Connection, file_id: UUID):
    query = """SELECT EXISTS(
                    SELECT 1 
                    FROM file f JOIN file_status fs ON f.id = fs.id 
                    WHERE f.id = $1 AND fs.status='infected'
            )"""
    result = await conn.fetchval(query, file_id)
    return result 

