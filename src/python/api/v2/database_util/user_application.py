# ==============================================================================
# File: src/python/api/v2/database_util/user_applications.py (New)
# Purpose: Contains all raw SQL queries for managing user applications.
# ==============================================================================
from asyncpg import Connection
from typing import List, Dict, Any, Optional
from uuid import UUID
from ..type_util.user_application import UserApplicationCreate, ApplicationStatus

async def create_user_application(conn: Connection, app_data: UserApplicationCreate) -> Dict[str, Any]:
    """Inserts a new user_application record into the database."""
    query = """
        INSERT INTO user_application 
            (email, name, username, justification, ngroup_id, account_type, provider_id, edpub_id, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending')
        RETURNING *;
    """
    row = await conn.fetchrow(
        query, app_data.email, app_data.name, app_data.username, app_data.justification,
        app_data.ngroup_id, app_data.account_type.value, app_data.provider_id, app_data.edpub_id
    )
    return dict(row)

async def get_user_application_by_id(conn: Connection, application_id: UUID) -> Optional[Dict[str, Any]]:
    """Retrieves a single user application by its ID."""
    return await conn.fetchrow("SELECT * FROM user_application WHERE id = $1", application_id)

async def list_user_applications(conn: Connection, ngroup_id: Optional[UUID] = None, status: Optional[ApplicationStatus] = None) -> List[Dict[str, Any]]:
    """Lists user applications, with optional filters for ngroup and status."""
    base_query = "SELECT * FROM user_application"
    conditions = []
    params = []
    
    if ngroup_id:
        params.append(ngroup_id)
        conditions.append(f"ngroup_id = ${len(params)}")
    if status:
        params.append(status.value)
        conditions.append(f"status = ${len(params)}")
        
    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)
        
    return await conn.fetch(base_query, *params)

async def update_application_status(conn: Connection, application_id: UUID, status: ApplicationStatus) -> Optional[Dict[str, Any]]:
    """Updates the status of a user application."""
    query = "UPDATE user_application SET status = $1 WHERE id = $2 RETURNING *;"
    return await conn.fetchrow(query, status.value, application_id)

async def delete_user_application(conn: Connection, application_id: UUID) -> bool:
    """Deletes a user application by its ID."""
    result = await conn.execute("DELETE FROM user_application WHERE id = $1", application_id)
    return result.strip() == "DELETE 1"

async def get_pending_application_by_user_id(conn: Connection, user_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Checks for a user application with a 'pending' status for a given user ID.
    The user ID here corresponds to the Keycloak 'sub' ID.
    """
    # Note: This assumes you will add a 'user_id' column to the user_application table.
    # If you are matching by email, the query would be different. Matching by ID is more reliable.
    query = "SELECT id FROM user_application WHERE user_id = $1 AND status = 'pending';"
    return await conn.fetchrow(query, user_id)