# ==============================================================================
# File: src/python/api/v2/database_util/user_application.py (Final)
# Purpose: Contains all raw SQL queries for managing user applications.
# Added explicit type casting in the list_user_applications query to
#      resolve the IndeterminateDatatypeError.
# ==============================================================================
from asyncpg import Connection
from typing import List, Dict, Any, Optional
from uuid import UUID
from v2.type_util.user_application import UserApplicationCreate, ApplicationStatus
import structlog

logger = structlog.get_logger(__name__)

async def create_user_application(conn: Connection, app_data: UserApplicationCreate, user_id: UUID) -> Dict[str, Any]:
    """Inserts a new user_application record into the database, including the user's Keycloak ID."""
    query = """
        INSERT INTO user_application 
            (user_id, email, name, username, justification, ngroup_id, account_type, provider_id, edpub_id, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'pending')
        RETURNING *;
    """
    row = await conn.fetchrow(
        query, user_id, app_data.email, app_data.name, app_data.username, app_data.justification,
        app_data.ngroup_id, app_data.account_type.value, app_data.provider_id, app_data.edpub_id
    )
    return dict(row)

async def get_user_application_by_id(conn: Connection, application_id: UUID) -> Optional[Dict[str, Any]]:
    """Retrieves a single user application by its ID."""
    row = await conn.fetchrow("SELECT * FROM user_application WHERE id = $1", application_id)
    return dict(row) if row else None

async def get_pending_application_by_user_id(conn: Connection, user_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Checks for a user application with a 'pending' status for a given user ID.
    """
    query = "SELECT id FROM user_application WHERE user_id = $1 AND status = 'pending';"
    row = await conn.fetchrow(query, user_id)
    logger.info("db.user_application.check_pending", user_id=str(user_id), application_found=(row is not None))
    return dict(row) if row else None

async def list_user_applications(conn: Connection, ngroup_id: Optional[UUID] = None, status: Optional[ApplicationStatus] = None) -> List[Dict[str, Any]]:
    """Lists user applications, with optional filters for ngroup and status."""
    base_query = "SELECT * FROM user_application"
    conditions = []
    params = []
    
    # --- CHANGE: Add explicit type casting for parameters ---
    if ngroup_id:
        params.append(ngroup_id)
        conditions.append(f"ngroup_id = ${len(params)}::uuid")
    if status:
        params.append(status.value)
        conditions.append(f"status = ${len(params)}::application_status")
        
    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)
    
    base_query += " ORDER BY applied DESC;"
        
    records = await conn.fetch(base_query, *params)
    return [dict(record) for record in records]

async def update_application_status(conn: Connection, application_id: UUID, status: ApplicationStatus) -> Optional[Dict[str, Any]]:
    """Updates the status of a user application."""
    query = "UPDATE user_application SET status = $1 WHERE id = $2 RETURNING *;"
    row = await conn.fetchrow(query, status.value, application_id)
    return dict(row) if row else None

async def delete_user_application(conn: Connection, application_id: UUID) -> bool:
    """Deletes a user application by its ID."""
    result = await conn.execute("DELETE FROM user_application WHERE id = $1", application_id)
    return result.strip() == "DELETE 1"
