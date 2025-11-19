# ==============================================================================
# File: src/python/api/v2/database_util/user_application.py
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

async def list_user_applications(
    conn: Connection,
    requesting_user: Dict[str, Any],
    active_ngroup_id: Optional[UUID] = None,
    status: Optional[ApplicationStatus] = None
) -> List[Dict[str, Any]]:
    """Lists user applications, filtered by the active ngroup and user role."""
    logger.info(
        "application.list.executing_query",
        user_roles=requesting_user.get('roles', []),
        active_ngroup_id=str(active_ngroup_id) if active_ngroup_id else None,
        status=status.value if status else None
    )

    user_roles = set(requesting_user.get('roles', []))
    params = []
    conditions = []
    
    # For non-privileged users, explicitly hide applications for the 'ESDIS Security' group.
    # This ensures a DAAC Manager can never see them.
    if 'admin' not in user_roles and 'security' not in user_roles:
        ESDIS_SECURITY_NGROUP_ID = UUID('0259fb55-1146-4461-ade2-57504e0c3ace')
        params.append(ESDIS_SECURITY_NGROUP_ID)
        conditions.append(f"ngroup_id != ${len(params)}::uuid")

    # If a DAAC is selected, ALL roles are strictly filtered by it.
    if active_ngroup_id:
        params.append(active_ngroup_id)
        conditions.append(f"ngroup_id = ${len(params)}::uuid")
    else:
        # If NO DAAC is selected:
        # Admins/Security see all applications from all groups.
        if 'admin' not in user_roles and 'security' not in user_roles:
            # All other roles see an empty list if no DAAC is selected.
            # This forces managers to select a DAAC to see applications.
            conditions.append("FALSE")

    if status:
        params.append(status.value)
        conditions.append(f"status = ${len(params)}::application_status")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"SELECT * FROM user_application {where_clause} ORDER BY applied DESC;"
    
    records = await conn.fetch(query, *params)
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
