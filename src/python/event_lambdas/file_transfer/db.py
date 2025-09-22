import structlog
from typing import List, Dict, Any, Optional
from uuid import UUID
import os 
import json
from datetime import datetime, timezone
from asyncpg import Connection
from asyncpg.exceptions import PostgresError

logger = structlog.get_logger(__file__)

async def fetch_destinations(conn:Connection, collection_ids:List[UUID]) -> Dict[UUID, Any]:
    query = """
        SELECT c.id as collection_id, e.path as path, e.config as config
        FROM collection c JOIN egress e ON c.egress_id = e.id
        WHERE e.type = 's3' AND c.id = ANY($1::UUID[])
    """
    try:
        records = await conn.fetch(query, collection_ids)
        destinations = {}
        for record in records:
            key = record["collection_id"]
            destinations[key] = {
                "path": record["path"],
                "config": json.loads((record["config"]))
            }
        return destinations
    except PostgresError as e:
        logger.error("db.fetch_destinations.postgres_error", collection_ids=[str(c) for c in collection_ids], exc_info=True)
        raise
    except Exception as e:
        logger.error("db.fetch_destinations.unexpected_error", collection_ids=[str(c) for c in collection_ids], exc_info=True)
        raise


async def fetch_file_metadata(conn:Connection, file_ids:List[UUID]) -> Dict[UUID, Any]: 
    # --- Added 'checksum' to the SELECT statement ---
    query = """
        SELECT id as file_id, collection_path, collection_id, name, checksum
        FROM file
        WHERE id = ANY($1::UUID[])
    """
    try:
        records = await conn.fetch(query, file_ids)
        file_metadata = {}
        for record in records:
            key = record["file_id"]
            file_metadata[key] = {
                "collection_path": record["collection_path"],
                "collection_id": record["collection_id"],
                "name": record["name"],
                "checksum": record["checksum"]
            }
        return file_metadata
    except PostgresError as e:
        logger.error("db.fetch_file_metadata.postgres_error", file_ids=[str(f) for f in file_ids], exc_info=True)
        raise
    except Exception as e:
        logger.error("db.fetch_file_metadata.unexpected_error", file_ids=[str(f) for f in file_ids], exc_info=True)
        raise


async def update_status_distributed(conn:Connection, file_ids:List[UUID]) -> bool:
    query = """
        UPDATE file_status
        SET status = $1, egress_start = NOW()
        WHERE id = ANY($2::UUID[]) 
    """
    try:
        result = await conn.execute(query, "distributed", file_ids)
        if not result or int(result.split(" ")[1]) == 0:
           logger.warning("db.update_status.failed_no_rows", file_ids=[str(f) for f in file_ids])
           return False
        logger.info("db.update_status.success", file_ids=[str(f) for f in file_ids])
        return True
    except PostgresError as e:
        logger.error("db.update_status.postgres_error", file_ids=[str(f) for f in file_ids], exc_info=True)
        raise
    except Exception as e:
        logger.error("db.update_status.unexpected_error", file_ids=[str(f) for f in file_ids], exc_info=True)
        raise


async def update_status_with_checksum_failure(
    conn: Connection,
    failure_details: List[Dict[str, Any]]
) -> bool:
    """
    Updates a batch of files to 'distributed' status while appending a checksum
    validation error to the scan_results JSONB column.
    """
    # This query uses the || operator to merge our new JSON object with any existing data in the column.
    query = """
        UPDATE file_status
        SET 
            status = 'distributed', 
            egress_start = NOW(),
            scan_results = scan_results || $2::jsonb
        WHERE id = $1::UUID;
    """
    try:
        # Prepare data for executemany: a list of tuples
        update_tuples = []
        for detail in failure_details:
            checksum_error_payload = {
                "checksum_validation": {
                    "status": "failed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "database_sha256": detail["db_checksum"],
                    "staging_file_sha256": detail["staging_checksum"] # Corrected key
                }
            }
            update_tuples.append(
                (detail["file_id"], json.dumps(checksum_error_payload))
            )

        # Use executemany for an efficient bulk update
        await conn.executemany(query, update_tuples)
        logger.info("db.update_status.checksum_failure_recorded", count=len(failure_details))
        return True
    except PostgresError as e:
        logger.error("db.update_status_checksum_failure.postgres_error", exc_info=True)
        raise
    except Exception as e:
        logger.error("db.update_status_checksum_failure.unexpected_error", exc_info=True)
        raise
