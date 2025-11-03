import structlog
from typing import List, Dict, Any
from uuid import UUID
import json
from datetime import datetime, timezone

from asyncpg import Connection
from asyncpg.exceptions import PostgresError

logger = structlog.get_logger(__name__)

async def fetch_batch_transfer_details(conn: Connection, file_ids: List[UUID]) -> Dict[UUID, Dict]:
    """
    Fetches all necessary file metadata and egress destination details in a single, efficient query.
    This query now explicitly filters for files that are ready for transfer.
    """
    query = """
        SELECT
            f.id as file_id,
            f.name,
            f.checksum,
            f.collection_path,
            f.size_bytes, 
            f.collection_id,
            f.type,
            e.path as egress_path,
            e.config as egress_config
        FROM file f
        JOIN collection c ON f.collection_id = c.id
        JOIN egress e ON c.egress_id = e.id
        WHERE f.id = ANY($1::UUID[])
          AND f.name != 'pending_upload' -- Ensure file has a real name
          AND f.checksum != 'pending';  -- Ensure file has a real checksum
    """
    try:
        records = await conn.fetch(query, file_ids)
        details_map = {}
        for record in records:
            file_id = record["file_id"]
            details_map[file_id] = {
                "file_info": {
                    "name": record["name"],
                    "checksum": record["checksum"],
                    "collection_path": record["collection_path"],
                    "size_bytes": record["size_bytes"],
                    "collection_id": record["collection_id"]
                },
                "egress": {
                    "path": record["egress_path"],
                    "config": json.loads(record["egress_config"])
                }
            }
        return details_map
    except PostgresError as e:
        logger.error("db.fetch_batch_transfer_details.postgres_error", file_ids=[str(f) for f in file_ids], exc_info=True)
        raise

async def safely_advance_file_status_batch(conn: Connection, file_ids: List[UUID], to_status: str):
    """
    Atomically and conditionally updates the status for a batch of files,
    ensuring it only moves forward. Includes detailed logging and error handling.
    """
    query = """
        UPDATE file_status
        SET
            status = $2::file_status_type,
            egress_start = CASE WHEN $2 = 'distributed' THEN NOW() ELSE egress_start END
        WHERE id = ANY($1::UUID[]) AND status = 'clean';
    """
    try:
        result = await conn.execute(query, file_ids, to_status)
        updated_count = int(result.split(" ")[1])

        if updated_count < len(file_ids):
            logger.warning(
                "db.advance_status.partial_success",
                to_status=to_status,
                attempted_count=len(file_ids),
                updated_count=updated_count,
                detail="Some files may not have been in the expected 'clean' state."
            )
        else:
            logger.info("db.safely_advance_file_status_batch.success", to_status=to_status, count=len(file_ids))

    except PostgresError as e:
        logger.error("db.safely_advance_file_status_batch.postgres_error", file_ids=[str(f) for f in file_ids], exc_info=True)
        raise

async def update_status_with_checksum_failure(conn: Connection, failure_details: List[Dict[str, Any]]):
    """Updates a batch of files to 'distributed' while logging a checksum validation failure."""
    query = """
        UPDATE file_status
        SET
            status = 'distributed',
            egress_start = NOW(),
            scan_results = scan_results || $2::jsonb
        WHERE id = $1::UUID AND status = 'clean';
    """
    try:
        update_tuples = []
        for detail in failure_details:
            checksum_error_payload = {
                "checksum_validation": {
                    "status": "failed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "database_sha256": detail["db_checksum"],
                    "staging_file_sha256": detail["staging_checksum"]
                }
            }
            update_tuples.append((detail["file_id"], json.dumps(checksum_error_payload)))
        
        await conn.executemany(query, update_tuples)
        logger.info("db.update.checksum_failure_recorded", count=len(failure_details))
    except PostgresError:
        logger.error("db.update_status_with_checksum_failure.postgres_error", exc_info=True)
        raise

