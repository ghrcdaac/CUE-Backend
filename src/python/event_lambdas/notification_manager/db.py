import logging
from uuid import UUID
from asyncpg import Connection

logger = logging.getLogger(__name__)

async def get_daac_manager_emails_for_file(conn: Connection, file_id: UUID) -> list[str]:
    """
    Finds the email addresses of all 'daac_manager' users associated with the
    ngroup of the user who uploaded a specific file.
    """
    # This role ID for 'daac_manager' should ideally come from a config/env var.
    DAAC_MANAGER_ROLE_ID = UUID('ef872fe7-92b9-45ec-ac19-80f4c478fd36')

    query = """
        WITH uploader_ngroup AS (
            -- Step 1: Find the ngroup of the original uploader
            SELECT ung.ngroup_id
            FROM file f
            JOIN cueuser_ngroup ung ON f.cueuser_uploaded = ung.cueuser_id
            WHERE f.id = $1
            LIMIT 1
        )
        -- Step 2: Find all users in that ngroup who have the DAAC Manager role
        SELECT u.email
        FROM cueuser u
        JOIN cueuser_role ur ON u.id = ur.cueuser_id
        JOIN cueuser_ngroup ung ON u.id = ung.cueuser_id
        WHERE ur.role_id = $2
          AND ung.ngroup_id = (SELECT ngroup_id FROM uploader_ngroup);
    """
    try:
        records = await conn.fetch(query, file_id, DAAC_MANAGER_ROLE_ID)
        emails = [record['email'] for record in records]
        logger.info(f"Found {len(emails)} DAAC Manager(s) for file {file_id}: {emails}")
        return emails
    except Exception as e:
        logger.error(f"Error fetching DAAC manager emails for file {file_id}: {e}", exc_info=True)
        return []