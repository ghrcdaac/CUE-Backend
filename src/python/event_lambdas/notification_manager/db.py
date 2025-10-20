import logging
from uuid import UUID
from asyncpg import Connection
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

async def get_infected_file_details(conn: Connection, file_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Finds all details for an infected file notification, including the emails of all
    'admin', 'security', 'daac_manager', and 'daac_staff' users in the file's group.
    """

    RECIPIENT_ROLES = ['admin', 'security', 'daac_manager', 'daac_staff']

    query = """
        WITH file_context AS (
            -- Step 1: Get the file's details and the ngroup it belongs to.
            SELECT
                f.name AS file_name,
                u.name AS uploader_name,
                c.short_name AS collection_name,
                c.ngroup_id
            FROM file f
            JOIN cueuser u ON f.cueuser_uploaded = u.id
            JOIN collection c ON f.collection_id = c.id
            WHERE f.id = $1
            LIMIT 1
        )
        -- Step 2: Aggregate the emails of all users who have one of the recipient roles AND are in that ngroup.
        SELECT
            (SELECT file_name FROM file_context) AS file_name,
            (SELECT uploader_name FROM file_context) AS uploader_name,
            (SELECT collection_name FROM file_context) AS collection_name,
            array_agg(DISTINCT u_recipients.email) AS recipient_emails
        FROM cueuser u_recipients
        JOIN cueuser_role ur ON u_recipients.id = ur.cueuser_id
        JOIN role r ON ur.role_id = r.id
        JOIN cueuser_ngroup ung ON u_recipients.id = ung.cueuser_id
        WHERE r.short_name = ANY($2::text[]) -- Check if role is in our list
          AND ung.ngroup_id = (SELECT ngroup_id FROM file_context)
        GROUP BY 1, 2, 3;
    """
    try:
        record = await conn.fetchrow(query, file_id, RECIPIENT_ROLES)
        
        if not record or not record['recipient_emails']:
            logger.warning(f"No notification details or recipients found for file {file_id}.")
            return None
        
        notification_details = dict(record)
        logger.info(f"Found {len(notification_details.get('recipient_emails', []))} recipient(s) for file {file_id}.")
        return notification_details

    except Exception as e:
        logger.error(f"Error fetching notification details for file {file_id}: {e}", exc_info=True)
        return None

async def get_new_application_details(conn: Connection, application_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Fetches details for a new application alert.
    - If it's a security application, it finds ALL system 'admins' and 'security' users.
    - Otherwise, it finds 'daac_manager' and 'admin' users within the application's specific ngroup.
    """
        
    # First, get the application's basic details, including its ngroup_id
    app_info_query = """
        SELECT
            ua.name AS user_name,
            ua.email AS user_email,
            ua.username AS user_username,
            ua.account_type,
            ua.justification,
            ua.ngroup_id,
            g.long_name AS ngroup_name
        FROM user_application ua
        JOIN ngroup g ON ua.ngroup_id = g.id
        WHERE ua.id = $1;
    """
    app_info = await conn.fetchrow(app_info_query, application_id)
    if not app_info:
        return None

    app_details = dict(app_info)
    ESDIS_SECURITY_NGROUP_ID = UUID('0259fb55-1146-4461-ade2-57504e0c3ace')
    
    recipient_emails = []

    if app_details['ngroup_id'] == ESDIS_SECURITY_NGROUP_ID:
        # This is a security application. Find all admins and security users in the system.
        recipient_roles = ['admin', 'security']
        recipients_query = """
            SELECT array_agg(DISTINCT u.email)
            FROM cueuser u
            JOIN cueuser_role ur ON u.id = ur.cueuser_id
            JOIN role r ON ur.role_id = r.id
            WHERE r.short_name = ANY($1::text[]);
        """
        recipient_emails = await conn.fetchval(recipients_query, recipient_roles)
    
    else:
        # This is a standard DAAC application. Use the original logic.
        recipient_roles = ['daac_manager', 'admin']
        recipients_query = """
            SELECT array_agg(DISTINCT u.email)
            FROM cueuser u
            JOIN cueuser_role ur ON u.id = ur.cueuser_id
            JOIN role r ON ur.role_id = r.id
            JOIN cueuser_ngroup ung ON u.id = ung.cueuser_id
            WHERE r.short_name = ANY($1::text[])
              AND ung.ngroup_id = $2;
        """
        recipient_emails = await conn.fetchval(recipients_query, recipient_roles, app_details['ngroup_id'])
        
    app_details['recipient_emails'] = recipient_emails or []
    
    return app_details

async def get_approved_user_details(conn: Connection, user_id: UUID) -> Optional[Dict[str, Any]]:
    """Fetches the name and email for a newly approved user."""
    query = "SELECT name AS user_name, email AS user_email FROM cueuser WHERE id = $1;"
    record = await conn.fetchrow(query, user_id)
    return dict(record) if record else None
