# ./src/python/event_lambdas/notification_manager/db.py
import logging
import json
from uuid import UUID
from asyncpg import Connection
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

async def get_notification_details_for_file(conn: Connection, file_id: UUID) -> Optional[Dict[str, Any]]:
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

async def get_infected_file_details(conn: Connection, hours: int) -> Optional[Dict[str,Any]]:
    """
    Finds all file details needed for an infected file notification, including:
    - The file name
    - The name of the user who uploaded it
    - The short_name of the collection it was uploaded to
    Args:
        conn: An active asyncpg database connection.
        file_id: The ID of the infected file.
    Returns:
        A dictionary containing the details, or None if the file is not found.
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
        WHERE fs.status = 'infected' AND upload_time >= NOW() - (INTERVAL '1 hour' * $2)
        GROUP BY user_ngroup,re.short_name,re.recipient_emails 
    """
    RECIPIENT_ROLES = ["ef872fe7-92b9-45ec-ac19-80f4c478fd36",
                       "c924d0d3-55af-49f3-bec1-d7fd4ed475e2",
                       "39677929-ba9b-426d-8c18-f607d669fcce"] 
    try:
        records = await conn.fetch(query, *(RECIPIENT_ROLES, hours))
        if not records:
            logger.warning("No infected file details")
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
