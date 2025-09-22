# ./src/python/event_lambdas/notification_manager/db.py
import logging
from uuid import UUID
from asyncpg import Connection
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

async def get_infected_file_details(conn: Connection, file_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Finds all details needed for an infected file notification, including:
    - The file name
    - The name of the user who uploaded it
    - The short_name of the collection it was uploaded to
    - A list of email addresses for all 'daac_manager' users in the uploader's group.

    Args:
        conn: An active asyncpg database connection.
        file_id: The ID of the infected file.

    Returns:
        A dictionary containing the details, or None if the file is not found.
    """
    # This role ID for 'daac_manager' should ideally come from a config/env var.
    DAAC_MANAGER_ROLE_ID = UUID('ef872fe7-92b9-45ec-ac19-80f4c478fd36')

    # This single query is more efficient than multiple separate lookups.
    query = """
        WITH uploader_details AS (
            -- Step 1: Get all file, uploader, and collection details in one go
            SELECT
                f.name AS file_name,
                u.name AS uploader_name,
                c.short_name AS collection_name, -- CORRECTED: Changed c.name to c.short_name
                ung.ngroup_id
            FROM file f
            JOIN cueuser u ON f.cueuser_uploaded = u.id
            JOIN collection c ON f.collection_id = c.id
            JOIN cueuser_ngroup ung ON u.id = ung.cueuser_id
            WHERE f.id = $1
            LIMIT 1
        )
        -- Step 2: Aggregate the emails of all DAAC managers in that ngroup
        SELECT
            (SELECT file_name FROM uploader_details) AS file_name,
            (SELECT uploader_name FROM uploader_details) AS uploader_name,
            (SELECT collection_name FROM uploader_details) AS collection_name,
            array_agg(u_managers.email) AS recipient_emails
        FROM cueuser u_managers
        JOIN cueuser_role ur ON u_managers.id = ur.cueuser_id
        JOIN cueuser_ngroup ung ON u_managers.id = ung.cueuser_id
        WHERE ur.role_id = $2 -- daac_manager role_id
          AND ung.ngroup_id = (SELECT ngroup_id FROM uploader_details)
        GROUP BY
            (SELECT file_name FROM uploader_details),
            (SELECT uploader_name FROM uploader_details),
            (SELECT collection_name FROM uploader_details);
    """
    try:
        record = await conn.fetchrow(query, file_id, DAAC_MANAGER_ROLE_ID)
        
        if not record or not record['recipient_emails']:
            logger.warning(f"No notification details or recipients found for file {file_id}.")
            return None
        
        # Convert the row to a dictionary for easy use.
        notification_details = dict(record)
        logger.info(f"Found {len(notification_details.get('recipient_emails', []))} DAAC Manager(s) for file {file_id}.")
        return notification_details

    except Exception as e:
        logger.error(f"Error fetching notification details for file {file_id}: {e}", exc_info=True)
        return None

async def get_infected_scheduled_file_details(conn: Connection, hours: int) -> Optional[Dict[UUID, Any]]:
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
    query = """
            WITH recipient_emails AS (
            SELECT ngroup_id, ng.short_name AS short_name, array_agg(u.email) AS recipient_emails
            FROM cueuser u
                JOIN cueuser_role ur ON u.id = ur.cueuser_id
                JOIN cueuser_ngroup ung ON u.id = ung.cueuser_id
                JOIN ngroup ng ON ung.ngroup_id = ng.id
            WHERE ur.role_id = ANY($1::uuid[]) 
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
                                    'scan_result', fs.scan_results->0->>'result',
                                    'virusName', fs.scan_results->0->'virusName',
                                    'date_scanned', fs.scan_results->0->'dateScanned')) AS file_details
            FROM file f
                JOIN cueuser u ON f.cueuser_uploaded = u.id
                JOIN collection c ON f.collection_id = c.id
                JOIN cueuser_ngroup ung ON u.id = ung.cueuser_id
                JOIN file_status fs ON f.id = fs.id
                JOIN recipient_emails re on re.ngroup_id = ung.ngroup_id
            WHERE fs.status = 'infected' AND fs.upload_time >= NOW() - (INTERVAL '1 hour' * $2)
            GROUP BY user_ngroup,re.short_name,re.recipient_emails 
    """
    RECIPIENT_ROLES = ["ef872fe7-92b9-45ec-ac19-80f4c478fd36",
                       "c924d0d3-55af-49f3-bec1-d7fd4ed475e2",
                       "39677929-ba9b-426d-8c18-f607d669fcce"] 
    try:
        records = await conn.fetch(query, *(RECIPIENT_ROLES, hours))
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

async def block_providers_uploading_infected_files(conn: Connection, hours: int, infected_file_threshold:int) -> Dict[UUID, Dict[UUID,Any]]:
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
            WHERE fs.status = 'infected' AND fs.upload_time >= NOW() - ((INTERVAL '1 hour')* $1)
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
        params = (hours, infected_file_threshold)
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
        raise e


async def get_new_application_details(conn: Connection, application_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Fetches all details needed for a new application alert, including the emails
    of all DAAC Managers in the application's ngroup.
    """
    DAAC_MANAGER_ROLE_ID = UUID('ef872fe7-92b9-45ec-ac19-80f4c478fd36')
    query = """
        WITH app_details AS (
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
            WHERE ua.id = $1
        )
        SELECT
            (SELECT user_name FROM app_details) AS user_name,
            (SELECT user_email FROM app_details) AS user_email,
            (SELECT user_username FROM app_details) AS user_username,
            (SELECT account_type FROM app_details) AS account_type,
            (SELECT justification FROM app_details) AS justification,
            (SELECT ngroup_name FROM app_details) AS ngroup_name,
            array_agg(u_managers.email) AS recipient_emails
        FROM cueuser u_managers
        JOIN cueuser_role ur ON u_managers.id = ur.cueuser_id
        JOIN cueuser_ngroup ung ON u_managers.id = ung.cueuser_id
        WHERE ur.role_id = $2 -- daac_manager role_id
          AND ung.ngroup_id = (SELECT ngroup_id FROM app_details)
        GROUP BY 1, 2, 3, 4, 5, 6;
    """
    record = await conn.fetchrow(query, application_id, DAAC_MANAGER_ROLE_ID)
    return dict(record) if record else None

async def get_approved_user_details(conn: Connection, user_id: UUID) -> Optional[Dict[str, Any]]:
    """Fetches the name and email for a newly approved user."""
    query = "SELECT name AS user_name, email AS user_email FROM cueuser WHERE id = $1;"
    record = await conn.fetchrow(query, user_id)
    return dict(record) if record else None