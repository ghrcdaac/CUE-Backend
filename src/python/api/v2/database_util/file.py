# File: src/python/api/v2/database_util/file.py (Updated)

from asyncpg import Connection, ForeignKeyViolationError
from typing import List, Optional, Dict, Any
from uuid import UUID
import structlog
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)

async def create_file_and_status_records(
    conn: Connection, file_id: UUID, file_name: str, file_type: str, user_id: UUID,
    size_bytes: int, collection_id: UUID, collection_path: Optional[str], checksum: str
):
    """Atomically creates a file and its initial file_status record in a transaction."""
    file_query = """
        INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, collection_path, edpub, checksum)
        VALUES ($1, $2, $3, $4, $5, $6, $7, FALSE, $8);
    """
    status_query = """
        INSERT INTO file_status (id, status, upload_time)
        VALUES ($1, 'unscanned', $2);
    """
    await conn.execute(
        file_query, file_id, file_name, file_type, user_id, size_bytes,
        collection_id, collection_path, checksum
    )
    await conn.execute(status_query, file_id, datetime.now(timezone.utc))

async def get_file_details(conn: Connection, file_id: UUID) -> Optional[Dict[str, Any]]:
    """Retrieves full file details by joining file and file_status tables."""
    query = """
        SELECT
            f.id, f.name, f.type, f.cueuser_uploaded, f.size_bytes, f.collection_id, f.collection_path, f.checksum,
            fs.status, fs.upload_time, fs.scan_start, fs.scan_end, fs.egress_start, fs.scan_results
        FROM file f
        LEFT JOIN file_status fs ON f.id = fs.id
        WHERE f.id = $1;
    """
    return await conn.fetchrow(query, file_id)

async def list_files_paginated(conn: Connection, ngroup_id: UUID, limit: int, offset: int) -> List[Dict[str, Any]]:
    """Lists a paginated set of files for a given ngroup."""
    query = """
        SELECT
            f.id, f.name, f.type, f.cueuser_uploaded, f.size_bytes, f.collection_id, f.collection_path, f.checksum,
            fs.status, fs.upload_time
        FROM file f
        JOIN collection c ON f.collection_id = c.id
        LEFT JOIN file_status fs ON f.id = fs.id
        WHERE c.ngroup_id = $1
        ORDER BY fs.upload_time DESC
        LIMIT $2 OFFSET $3;
    """
    return await conn.fetch(query, ngroup_id, limit, offset)

async def count_files_for_ngroup(conn: Connection, ngroup_id: UUID) -> int:
    """Counts the total number of files in a given ngroup."""
    query = """
        SELECT COUNT(f.id)
        FROM file f
        JOIN collection c ON f.collection_id = c.id
        WHERE c.ngroup_id = $1;
    """
    count = await conn.fetchval(query, ngroup_id)
    return count or 0

async def update_file(conn: Connection, file_id: UUID, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Updates an existing file record in the database."""
    fields, values = list(update_data.keys()), list(update_data.values())
    set_clause = ", ".join(f"{field} = ${i+1}" for i, field in enumerate(fields))
    query = f"UPDATE file SET {set_clause} WHERE id = ${len(fields) + 1} RETURNING id;"
    
    updated_id = await conn.fetchval(query, *values, file_id)
    return updated_id is not None


async def delete_file(conn: Connection, file_id: UUID) -> bool:
    """Deletes a file record. Related records in other tables are handled by ON DELETE CASCADE."""
    try:
        result = await conn.execute("DELETE FROM file WHERE id = $1", file_id)
        return result.strip() == "DELETE 1"
    except ForeignKeyViolationError as e:
        logger.warning("db.file.delete.failed_fk", file_id=str(file_id), error=str(e))
        raise ValueError("Cannot delete this file because it is still referenced by other records.") from e