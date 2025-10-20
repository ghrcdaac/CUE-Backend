import logging
import json
from uuid import UUID
from asyncpg import Connection
from typing import Dict, Any, Optional, List
from datetime import timedelta

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

async def get_infected_scheduled_file_details(conn: Connection, time_threshold: timedelta) -> Optional[Dict[UUID, Any]]:
    """
    Finds all file details needed for an infected file notification, including:
    - The file name
    - The name of the user who uploaded it
    - The short_name of the collection it was uploaded to
    Args:
        conn: An active asyncpg database connection.
        hours: How many hours to search back for infected files.
    Returns:
        A dictionary containing the details grouped by ngroup_id, or None if the file is not found.
    """
    # The index of the scan_result effected by other items stored in the scan_results column
    query = """
            WITH recipient_emails AS (
            SELECT ngroup_id, ng.short_name AS short_name, array_agg(u.email) AS recipient_emails
            FROM cueuser u
                JOIN cueuser_role ur ON u.id = ur.cueuser_id
                JOIN cueuser_ngroup ung ON u.id = ung.cueuser_id
                JOIN ngroup ng ON ung.ngroup_id = ng.id
                JOIN role r ON r.id = ur.role_id
            WHERE r.short_name = ANY($1::text[]) 
            GROUP BY ngroup_id, ng.short_name
            )
            SELECT 
                ung.ngroup_id AS user_ngroup,
                re.short_name,
                re.recipient_emails,
                JSONB_AGG(
                    JSONB_BUILD_OBJECT('file_id', f.id,
                                    'file_name', f.name,
                                    'uploader_name', u.name,
                                    'collection_name', c.short_name,
                                    'user_ngroup', ung.ngroup_id,
                                    'scan_result', scan_result,
                                    'virusName', virusName,
                                    'date_scanned', data_scanned)) AS file_details
            FROM file f
                JOIN cueuser u ON f.cueuser_uploaded = u.id
                JOIN collection c ON f.collection_id = c.id
                JOIN cueuser_ngroup ung ON u.id = ung.cueuser_id
                JOIN file_status fs ON f.id = fs.id
                JOIN recipient_emails re on re.ngroup_id = ung.ngroup_id,
                LATERAL jsonb_path_query(fs.scan_results, '$[*].result') as scan_result,
                LATERAL jsonb_path_query(fs.scan_results, '$[*].virusName') as virusName,
                LATERAL jsonb_path_query(fs.scan_results, '$[*].dateScanned') as data_scanned
            WHERE fs.status = 'infected' AND fs.upload_time >= (NOW() - $2::INTERVAL)
            GROUP BY user_ngroup,re.short_name,re.recipient_emails 
    """
    RECIPIENT_ROLES = ["admin", "security", "daac_manager", "daac_staff"] 
    try:
        records = await conn.fetch(query, *(RECIPIENT_ROLES, time_threshold))
        if not records:
            logger.info("No infected file details")
            return None

        notification_details = {}
        for record in records:
            key = record['user_ngroup']
            notification_details[key] = {'short_name': record['short_name'],
                                         'recipient_emails': record['recipient_emails'],
                                         'file_details': json.loads(record['file_details'])}
        logger.info("Found infected files")
        return notification_details
    except Exception as e:
        logger.error(f"Error fetching notification details :{e}", exc_info=True)
        return None

async def block_providers_uploading_infected_files(conn: Connection, time_threshold: timedelta, infected_file_threshold:int) -> Dict[UUID, Dict[UUID,Any]]:
    """
    Finds all providers that have uploaded infected files equal to or greater than the threshold with the given hours
    Then blocks these providers from uploading.
    - Collects the provider's id and provider's short name.
    Args:
        conn: An active asyncpg database connection.
        hours: How many hours to search back for infected files.
        infected_file_threshold: The amount of infected files it takes to block a provider.
    """
    
    query = """
        WITH infected_provider_uploads AS (
            SELECT
                p.id AS provider_id,
                p.short_name AS provider_name,
                p.ngroup_id AS provider_ngroup 
            FROM file f
            JOIN file_status fs ON f.id = fs.id
            JOIN cueuser_provider up ON f.cueuser_uploaded = up.cueuser_id
            JOIN provider p ON p.id = up.provider_id 
            WHERE fs.status = 'infected' AND fs.upload_time >= (NOW() - $1::INTERVAL)
            GROUP BY p.id
            HAVING (count(f.id) >= $2)
        )
        SELECT provider_ngroup,
            array_agg(provider_id) as provider_ids,
            JSONB_AGG(
                JSON_BUILD_OBJECT(
                    'provider_id', provider_id,
                    'provider_name', provider_name
                )
            ) as provider_details
        FROM infected_provider_uploads
        GROUP BY provider_ngroup
    """ 
    # This query gets details grouped by ngroup_id of providers that have uploaded infected files over the threshold
    try:
        params = (time_threshold, infected_file_threshold)
        records = await conn.fetch(query, *params)
        if not records:
            logger.info("No users to block")
            return {}

        blocked_providers = {} 
        provider_ids = []
        # extract the provider_ids across all ngroups and prepare details for processing 
        for record in records:
            key = record["provider_ngroup"] 
            blocked_providers[key] = json.loads(record["provider_details"])
            provider_ids.extend(record["provider_ids"])

        logger.info("Found users to block")
        # bulk block all providers that have uploaded pass threshold 
        if provider_ids:
           await block_providers(conn, provider_ids)
        return blocked_providers
    except Exception as e:
        logger.error(f"Error finding providers to block or blocking providers: {e}", exc_info=True)
        return {} 

async def block_providers(conn:Connection, provider_ids:List[UUID]):
    """
    Helper function for block_provider_uploading_infected_file
    Disables the "Can Upload" permission for every provider who's id is the provider_ids list 
    Args: 
        providers_ids: A list of providers ids to block from uploading.
    """
     
    query = """
        UPDATE provider
        SET can_upload = false
        WHERE id = ANY($1::uuid[])
    """ 
    try: 
        result = await conn.fetch(query, provider_ids)
        return result 
    except Exception as e:
        logger.error(f"Error blocking providers : {e}", exc_info=True)

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
