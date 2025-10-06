import structlog
from typing import List, Dict, Any
from uuid import UUID
import json
from datetime import datetime, timezone
from asyncpg import Connection
from asyncpg.exceptions import PostgresError

logger = structlog.get_logger(__name__)

async def fetch_batch_transfer_details(conn: Connection, file_ids: List[UUID]) -> Dict[UUID, Any]:
    """
    Consolidates fetching file metadata and egress destinations into a single, efficient query.
    Crucially, it filters out files that are not yet ready for transfer.
    """
    query = """
        SELECT
            f.id as file_id,
            f.collection_path,
            f.collection_id,
            f.name,
            f.checksum,
            e.path as egress_path,
            e.config as egress_config
        FROM file f
        JOIN collection c ON f.collection_id = c.id
        JOIN egress e ON c.egress_id = e.id
        WHERE
            e.type = 's3' AND
            f.id = ANY($1::UUID[]) AND
            f.name != 'pending_upload' AND
            f.checksum != 'pending';
    """
    try:
        records = await conn.fetch(query, file_ids)
        details = {}
        for record in records:
            file_id = record["file_id"]
            details[file_id] = {
                "file_info": {
                    "collection_path": record["collection_path"],
                    "collection_id": record["collection_id"],
                    "name": record["name"],
                    "checksum": record["checksum"]
                },
                "egress": {
                    "path": record["egress_path"],
                    "config": json.loads(record["egress_config"])
                }
            }
        return details
    except PostgresError as e:
        logger.error("db.fetch_batch_transfer_details.postgres_error", file_ids=[str(f) for f in file_ids], exc_info=True)
        raise

async def safely_advance_file_status_batch(conn: Connection, file_ids: List[UUID], target_status: str) -> int:
    """
    Atomically and conditionally advances the status for a batch of files from 'clean' to a target status.
    Returns the number of rows that were successfully updated.
    """
    query = """
        UPDATE file_status
        SET
            status = $2::file_status_type,
            egress_start = NOW()
        WHERE
            id = ANY($1::UUID[]) AND status = 'clean';
    """
    try:
        result = await conn.execute(query, file_ids, target_status)
        updated_count = int(result.split(" ")[1])
        if updated_count < len(file_ids):
            logger.warning("db.advance_status.partial_success",
                           attempted_count=len(file_ids),
                           updated_count=updated_count,
                           detail="Some files may not have been in 'clean' state.")
        return updated_count
    except PostgresError as e:
        logger.error("db.safely_advance_file_status_batch.postgres_error", file_ids=[str(f) for f in file_ids], exc_info=True)
        raise

async def update_status_with_checksum_failure(conn: Connection, failure_details: List[Dict[str, Any]]) -> bool:
    """
    Updates a batch of files to 'distributed' status while appending a checksum
    validation error to the scan_results JSONB column. This operation is conditional
    on the file status being 'clean'.
    """
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
            update_tuples.append(
                (detail["file_id"], json.dumps(checksum_error_payload))
            )

        await conn.executemany(query, update_tuples)
        logger.info("db.update.checksum_failure_recorded", count=len(failure_details))
        return True
    except PostgresError as e:
        logger.error("db.update_status_with_checksum_failure.postgres_error", exc_info=True)
        raise

