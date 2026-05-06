import logging
import json
from uuid import UUID
from asyncpg import Connection
from typing import Dict, Any, Optional, List, Tuple
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
        SELECT
            (SELECT file_name FROM file_context) AS file_name,
            (SELECT uploader_name FROM file_context) AS uploader_name,
            (SELECT collection_name FROM file_context) AS collection_name,
            array_agg(DISTINCT u_recipients.email) AS recipient_emails
        FROM cueuser u_recipients
        JOIN cueuser_role ur ON u_recipients.id = ur.cueuser_id
        JOIN role r ON ur.role_id = r.id
        JOIN cueuser_ngroup ung ON u_recipients.id = ung.cueuser_id
        WHERE r.short_name = ANY($2::text[])
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

async def get_infected_scheduled_file_details(conn: Connection) -> Optional[Dict[UUID, Any]]:
    """
    Finds all file details for infected files that have not yet had a notification sent.
    """
    # Define recipient roles directly in the query context for clarity
    RECIPIENT_ROLES = ["admin", "security", "daac_manager", "daac_staff"]
    
    query = """
        WITH RelevantInfectedFiles AS (
            -- Select infected files that have not been notified
            SELECT
                f.id AS file_id,
                f.name AS file_name,
                f.collection_id,
                u.name AS uploader_name,
                fs.scan_results,
                fs.scan_end -- Use scan_end for ordering
            FROM file f
            JOIN file_status fs ON f.id = fs.id
            JOIN cueuser u ON f.cueuser_uploaded = u.id
            WHERE fs.status = 'infected'
              AND fs.notification_sent_at IS NULL -- Find files not yet reported
            ORDER BY fs.scan_end ASC -- Process oldest first
            LIMIT 500 -- Safety valve for large backlogs
        ),
        FileDetailsGroupedByCollectionNgroup AS (
            SELECT
                c.ngroup_id,
                ng.short_name AS ngroup_short_name,
                JSONB_AGG(
                    JSONB_BUILD_OBJECT(
                        'file_id', rif.file_id,
                        'file_name', rif.file_name,
                        'uploader_name', rif.uploader_name,
                        'collection_name', c.short_name,
                        'scan_result', scan_res ->> 'result',
                        'virusName', COALESCE(scan_res -> 'scanResults' -> 0 -> 'virusName', scan_res -> 'virusName'),
                        'date_scanned', scan_res ->> 'dateScanned',
                        'uploader_ip', rif.scan_results -> 0 ->> 'ip_address'
                    ) ORDER BY rif.scan_end ASC
                ) AS file_details_json
            FROM RelevantInfectedFiles rif
            JOIN collection c ON rif.collection_id = c.id
            JOIN ngroup ng ON c.ngroup_id = ng.id
            JOIN LATERAL jsonb_array_elements(
                CASE
                    WHEN jsonb_typeof(rif.scan_results) = 'array' THEN rif.scan_results
                    WHEN jsonb_typeof(rif.scan_results) = 'object' THEN 
                        -- Wraps single event objects in an array safely
                        jsonb_build_array(rif.scan_results) 
                    ELSE '[]'::jsonb
                END
            ) AS scan_res ON TRUE
            WHERE scan_res ->> 'result' = 'Infected' 
            GROUP BY c.ngroup_id, ng.short_name
        )
        -- Final Select: Join aggregated file details with correctly scoped recipients
        SELECT
            fdg.ngroup_id,
            fdg.ngroup_short_name,
            fdg.file_details_json,
            -- Aggregate recipient emails specifically for this ngroup_id
            (
                SELECT array_agg(DISTINCT u.email)
                FROM cueuser u
                JOIN cueuser_role ur ON u.id = ur.cueuser_id
                JOIN role r ON ur.role_id = r.id
                JOIN cueuser_ngroup ung ON u.id = ung.cueuser_id
                WHERE r.short_name = ANY($1::text[]) 
                  AND ung.ngroup_id = fdg.ngroup_id 
            ) AS recipient_emails
        FROM FileDetailsGroupedByCollectionNgroup fdg;
    """
    try:
        # Pass recipient roles as the first parameter
        records = await conn.fetch(query, RECIPIENT_ROLES)
        if not records:
            logger.info("No new infected file details found to report.")
            return None
            
        notification_details = {}
        for record in records:
            key = record['ngroup_id'] # Use the explicitly selected ngroup_id
            
            # Parse the aggregated file details JSON
            try:
                file_details_list = json.loads(record['file_details_json']) if isinstance(record['file_details_json'], str) else record['file_details_json']
                if file_details_list is None:
                       file_details_list = []
                elif not isinstance(file_details_list, list):
                       file_details_list = [file_details_list]

            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse file_details_json JSONB for ngroup_id={key}, raw_details={record['file_details_json']}, error={e}")
                file_details_list = [] # Avoid crashing, log the error

            notification_details[key] = {
                'short_name': record['ngroup_short_name'], # Use the explicitly selected short_name
                'recipient_emails': record['recipient_emails'] or [], # Handle potential NULL from subquery
                'file_details': file_details_list # Use the parsed list
            }
            
        count = len(notification_details)
        logger.info(f"Aggregated infected file details by {count} ngroup(s).")
        return notification_details
        
    except Exception as e:
        logger.error(f"Error fetching scheduled notification details: {e}", exc_info=True)
        return None


async def get_providers_exceeding_threshold(conn: Connection, time_threshold: timedelta, infected_file_threshold: int) -> Dict[UUID, List[Dict[str, Any]]]:
    """
    Finds providers that (a) exceeded the threshold in the lookback window,
    (b) are currently blocked, and (c) have not had a notification sent yet.
    Returns details grouped by the collection's ngroup_id.
    """
    query = """
        WITH infected_collection_providers AS (
            -- Find providers linked to collections where infected files were uploaded
            SELECT DISTINCT
                c.provider_id,
                p.short_name AS provider_name,
                c.ngroup_id AS collection_ngroup,
                p.can_upload,
                p.reason,
                -- Count infected files per provider *within this time window*
                COUNT(f.id) OVER (PARTITION BY c.provider_id) as infected_count
            FROM file f
            JOIN file_status fs ON f.id = fs.id
            JOIN collection c ON f.collection_id = c.id
            JOIN provider p ON c.provider_id = p.id
            WHERE fs.status = 'infected'
              AND fs.scan_end >= (NOW() - $1::INTERVAL)
        )
        -- Aggregate the details for reporting, grouped by the collection's ngroup
        SELECT
            icp.collection_ngroup,
            JSONB_AGG(
                JSONB_BUILD_OBJECT(
                    'provider_id', icp.provider_id,
                    'provider_name', icp.provider_name,
                    'is_currently_blocked', NOT icp.can_upload,
                    'current_reason', icp.reason
                )
            ) as provider_details
        FROM infected_collection_providers icp
        -- Join provider table to check notification status
        JOIN provider p ON icp.provider_id = p.id
        WHERE icp.infected_count >= $2 -- Apply threshold filter
          AND p.can_upload = false -- Only report providers that are *actually* blocked
          AND p.last_block_notification_at IS NULL -- Only report if we haven't notified
        GROUP BY icp.collection_ngroup;
    """
    try:
        params = (time_threshold, infected_file_threshold)
        records = await conn.fetch(query, *params)
        if not records:
            logger.info("No new provider blocks to report.")
            return {}

        providers_exceeding_threshold = {}
        for record in records:
            key = record["collection_ngroup"]
            try:
                details_list = json.loads(record["provider_details"]) if isinstance(record["provider_details"], str) else record["provider_details"]
            except json.JSONDecodeError:
                logger.error(f"Failed to parse provider_details JSONB for ngroup_id={key}, raw_details={record['provider_details']}")
                details_list = []
            providers_exceeding_threshold[key] = details_list

        count = len(providers_exceeding_threshold)
        logger.info(f"Found {count} ngroup(s) with providers exceeding threshold (by collection).")
        return providers_exceeding_threshold
    except Exception as e:
        logger.error(f"Error finding providers exceeding threshold (by collection): {e}", exc_info=True)
        return {}



async def get_new_application_details(conn: Connection, application_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Fetches details for a new application alert.
    - If it's a security application, it finds ALL system 'admins' and 'security' users.
    - Otherwise, it finds 'daac_manager' and 'admin' users within the application's specific ngroup.
    """
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
        # This is a standard DAAC application.
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

async def get_ngroup_recipient_emails(conn: Connection, ngroup_id: UUID) -> Tuple[List[str], Optional[str]]:
    """Fetches recipient emails AND the short_name for a specific ngroup."""
    RECIPIENT_ROLES = ["admin", "security", "daac_manager", "daac_staff"]
    query = """
        SELECT 
            g.short_name, -- Fetch the group's short name
            array_agg(DISTINCT u.email) FILTER (WHERE u.email IS NOT NULL) AS emails -- Aggregate emails
        FROM ngroup g
        LEFT JOIN cueuser_ngroup ung ON g.id = ung.ngroup_id
        LEFT JOIN cueuser u ON ung.cueuser_id = u.id
        LEFT JOIN cueuser_role ur ON u.id = ur.cueuser_id
        LEFT JOIN role r ON ur.role_id = r.id AND r.short_name = ANY($1::text[])
        WHERE g.id = $2
        GROUP BY g.short_name; -- Group by the name we're selecting
    """
    try:
        result = await conn.fetchrow(query, RECIPIENT_ROLES, ngroup_id)
        if result:
            emails = result['emails'] or []
            short_name = result['short_name']
            return emails, short_name
        else:
            logger.warning(f"db.get_ngroup_details.not_found for ngroup_id={ngroup_id}")
            return [], None # Return empty list and None if group not found
    except Exception as e:
        logger.error(f"db.get_ngroup_recipients.failed for ngroup_id={ngroup_id}", exc_info=True)
        return [], None # Return empty list and None on error
    


async def mark_files_as_notified(conn: Connection, file_ids: List[UUID]):
    """Sets notification_sent_at for a list of file IDs."""
    if not file_ids:
        return
    try:
        await conn.execute(
            "UPDATE file_status SET notification_sent_at = NOW() WHERE id = ANY($1::uuid[])",
            file_ids
        )
        logger.info(f"Marked {len(file_ids)} files as notified.")
    except Exception as e:
        logger.error(f"Failed to mark files as notified", exc_info=True)
        raise

async def mark_providers_as_notified(conn: Connection, provider_ids: List[UUID]):
    """Sets last_block_notification_at for a list of provider IDs."""
    if not provider_ids:
        return
    try:
        await conn.execute(
            "UPDATE provider SET last_block_notification_at = NOW() WHERE id = ANY($1::uuid[])",
            provider_ids
        )
        logger.info(f"Marked {len(provider_ids)} providers as notified.")
    except Exception as e:
        logger.error(f"Failed to mark providers as notified", exc_info=True)
        raise