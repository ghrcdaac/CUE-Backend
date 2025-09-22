# File: src/python/api/v2/database_util/file.py

from asyncpg import Connection, ForeignKeyViolationError
from typing import List, Optional, Dict, Any
from uuid import UUID
import structlog
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)

# --- FUNCTION ADDED: Restored the function needed by the upload process ---
async def create_file_and_status_records(
    conn: Connection, file_id: UUID, file_name: str, file_type: str, user_id: UUID,
    size_bytes: int, collection_id: UUID, collection_path: Optional[str], checksum: str
):
    """Atomically creates a file and its initial 'unscanned' file_status record in a transaction."""
    file_query = """
        INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, collection_path, edpub, checksum)
        VALUES ($1, $2, $3, $4, $5, $6, $7, FALSE, $8);
    """
    status_query = """
        INSERT INTO file_status (id, status, upload_time)
        VALUES ($1, 'unscanned', $2);
    """
    # These are executed within a transaction in the calling utils function
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

async def find_files_by_name(
    conn: Connection,
    requesting_user: Dict[str, Any],
    active_ngroup_id: Optional[UUID],
    file_name: str
) -> List[Dict[str, Any]]:
    """Retrieves files by name, filtered by the active ngroup and user role."""
    user_roles = set(requesting_user.get('roles', []))
    params: list[Any] = [file_name]
    
    base_query = """
        SELECT f.id, f.name, f.type, f.cueuser_uploaded, f.size_bytes, f.collection_id, f.collection_path, f.checksum, fs.status, fs.upload_time
        FROM file f
        JOIN collection c ON f.collection_id = c.id
        LEFT JOIN file_status fs ON f.id = fs.id
    """
    where_conditions = ["f.name = $1"]

    if active_ngroup_id:
        params.append(active_ngroup_id)
        where_conditions.append(f"c.ngroup_id = ${len(params)}")
    else:
        if 'admin' not in user_roles and 'security' not in user_roles:
            where_conditions.append("FALSE")

    query = f"{base_query} WHERE {' AND '.join(where_conditions)} ORDER BY fs.upload_time DESC;"
    return await conn.fetch(query, *params)


async def list_files_paginated(
    conn: Connection,
    requesting_user: Dict[str, Any],
    active_ngroup_id: Optional[UUID],
    limit: int,
    offset: int,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Lists a paginated set of files, filtered by the active ngroup and user role."""
    user_roles = set(requesting_user.get('roles', []))
    params: list[Any] = []
    
    base_query = """
        SELECT f.id, f.name, f.type, f.cueuser_uploaded, f.size_bytes, f.collection_id, f.collection_path, f.checksum, fs.status, fs.upload_time
        FROM file f
        JOIN collection c ON f.collection_id = c.id
        LEFT JOIN file_status fs ON f.id = fs.id
    """
    where_conditions = []

    if active_ngroup_id:
        params.append(active_ngroup_id)
        where_conditions.append(f"c.ngroup_id = ${len(params)}")
    else:
        if 'admin' not in user_roles and 'security' not in user_roles:
            where_conditions.append("FALSE")

    if status:
        params.append(status)
        where_conditions.append(f"fs.status = ${len(params)}")
        
    where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
    query = f"{base_query} {where_clause} ORDER BY fs.upload_time DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
    params.extend([limit, offset])
    
    return await conn.fetch(query, *params)


async def count_files_for_ngroup(
    conn: Connection,
    requesting_user: Dict[str, Any],
    active_ngroup_id: Optional[UUID],
    status: Optional[str] = None
) -> int:
    """Counts files, filtered by the active ngroup and user role."""
    user_roles = set(requesting_user.get('roles', []))
    params: list[Any] = []

    base_query = "SELECT COUNT(f.id) FROM file f JOIN collection c ON f.collection_id = c.id"
    join_clause = " LEFT JOIN file_status fs ON f.id = fs.id" if status else ""
    where_conditions = []

    if active_ngroup_id:
        params.append(active_ngroup_id)
        where_conditions.append(f"c.ngroup_id = ${len(params)}")
    else:
        if 'admin' not in user_roles and 'security' not in user_roles:
            where_conditions.append("FALSE")

    if status:
        params.append(status)
        where_conditions.append(f"fs.status = ${len(params)}")

    where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
    query = f"{base_query}{join_clause} {where_clause}"
    
    count = await conn.fetchval(query, *params)
    return count or 0

async def delete_file(conn: Connection, file_id: UUID) -> bool:
    """Deletes a file record. Assumes ON DELETE CASCADE is set for related tables."""
    try:
        deleted_id = await conn.fetchval("DELETE FROM file WHERE id = $1 RETURNING id", file_id)
        return deleted_id is not None
    except ForeignKeyViolationError as e:
        logger.warning("db.file.delete.failed_fk", file_id=str(file_id), error=str(e))
        raise ValueError("Cannot delete this file because it is still referenced.") from e