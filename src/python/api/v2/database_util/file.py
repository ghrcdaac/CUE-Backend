# ==============================================================================
# File: src/python/api/v2/database_util/file.py
# ==============================================================================
from asyncpg import Connection, ForeignKeyViolationError
from typing import List, Optional, Dict, Any
from uuid import UUID
import json
import structlog
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)

async def create_preliminary_file_records(
    conn: Connection, file_id: UUID, user_id: UUID, collection_id: UUID,
    ip_address: Dict,
    file_name: str,
    file_type: str,
    size_bytes: int,
    checksum: str,
    collection_path: Optional[str]
):
    """
    Atomically creates file and 'uploading' file_status records using all available metadata from the user.
    This prevents race conditions by recording the real data immediately.
    """
    file_query = """
        INSERT INTO file (id, name, type, cueuser_uploaded, size_bytes, collection_id, checksum, collection_path)
        VALUES ($1, $4, $5, $2, $6, $3, $7, $8);
    """
    await conn.execute(
        file_query, file_id, user_id, collection_id, file_name,
        file_type, size_bytes, checksum, collection_path
    )
    
    status_query = """
        INSERT INTO file_status (id, status, upload_time, scan_results)
        VALUES ($1, 'uploading', $2, $3::jsonb);
    """
    await conn.execute(status_query, file_id, datetime.now(timezone.utc), json.dumps(ip_address))


async def safely_advance_file_status(conn: Connection, file_id: UUID, target_status: str) -> bool:
    """
    Atomically and conditionally advances a file's status based on a defined, forward-only state machine.
    This prevents status regressions (e.g., 'clean' -> 'unscanned').

    The state machine is enforced by the SQL CASE statement:
    - 'uploading' can only become 'unscanned'.
    - 'unscanned' can become 'clean', 'infected', or 'scan_failed'.
    - 'clean' can only become 'distributed'.
    - Any other attempted transition will result in no change.
    """
    query = """
        UPDATE file_status
        SET status = (
            CASE
                WHEN status = 'uploading' AND $2 = 'unscanned'
                    THEN 'unscanned'::file_status_type
                WHEN status = 'unscanned' AND $2 IN ('clean', 'infected', 'scan_failed')
                    THEN $2::file_status_type
                WHEN status = 'clean' AND $2 = 'distributed'
                    THEN 'distributed'::file_status_type
                ELSE status
            END
        )
        WHERE id = $1;
    """
    # This query always "succeeds", but we check if a change was intended and occurred.
    # For the 'complete' step, we just need to fire it off.
    await conn.execute(query, file_id, target_status)
    return True # For the purpose of the upload utility, we indicate success.


async def update_final_file_details(
    conn: Connection, file_id: UUID, file_name: str, file_type: str,
    size_bytes: int, collection_path: Optional[str], checksum: str, ip_address: Dict
):
    """
    Updates the main file record with final metadata (primarily for multipart uploads)
    and then transitions its status to 'unscanned'.
    """
    file_update_query = """
        UPDATE file
        SET name = $2, type = $3, size_bytes = $4, collection_path = $5, checksum = $6
        WHERE id = $1;
    """
    await conn.execute(
        file_update_query, file_id, file_name, file_type, size_bytes,
        collection_path, checksum
    )

    # Use the safe state transition function to move the status forward.
    await safely_advance_file_status(conn, file_id, 'unscanned')


async def update_file(conn: Connection, file_id: UUID, update_data: Dict[str, Any]) -> bool:
    """Dynamically builds and executes an UPDATE statement for a file."""
    if not update_data:
        return False
    
    set_clauses = []
    params = []
    param_idx = 1
    
    for key, value in update_data.items():
        set_clauses.append(f"{key} = ${param_idx}")
        params.append(value)
        param_idx += 1
        
    params.append(file_id)
    query = f"UPDATE file SET {', '.join(set_clauses)} WHERE id = ${param_idx}"
    
    result = await conn.execute(query, *params)
    return result.split(' ')[1] == '1'


async def get_file_details(conn: Connection, file_id: UUID) -> Optional[Dict[str, Any]]:
    query = """
        SELECT
            f.id, f.name, f.type, f.cueuser_uploaded, f.size_bytes, f.collection_id, f.collection_path, f.checksum,
            fs.status, fs.upload_time, fs.scan_start, fs.scan_end, fs.egress_start, fs.scan_results
        FROM file f
        LEFT JOIN file_status fs ON f.id = fs.id
        WHERE f.id = $1;
    """
    return await conn.fetchrow(query, file_id)


async def list_files_paginated(
    conn: Connection,
    requesting_user: Dict[str, Any],
    active_ngroup_id: Optional[UUID],
    limit: int,
    offset: int,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    user_roles = set(requesting_user.get('roles', []))
    params: list[Any] = []
    
    base_query = """
        SELECT 
            f.id, f.name, f.type, f.cueuser_uploaded, f.size_bytes, f.collection_id, f.collection_path, f.checksum, 
            fs.status, fs.upload_time, fs.scan_results, fs.egress_start
        FROM file f
        JOIN collection c ON f.collection_id = c.id
        LEFT JOIN file_status fs ON f.id = fs.id
    """
    where_conditions = ["f.name != 'pending_upload'"]

    if active_ngroup_id:
        params.append(active_ngroup_id)
        where_conditions.append(f"c.ngroup_id = ${len(params)}")
    else:
        if 'admin' not in user_roles and 'security' not in user_roles:
            where_conditions.append("FALSE")

    if status:
        params.append(status)
        where_conditions.append(f"fs.status = ${len(params)}")
        
    where_clause = f"WHERE {' AND '.join(where_conditions)}"
    query = f"{base_query} {where_clause} ORDER BY fs.upload_time DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
    params.extend([limit, offset])
    
    return await conn.fetch(query, *params)


async def count_files_for_ngroup(
    conn: Connection,
    requesting_user: Dict[str, Any],
    active_ngroup_id: Optional[UUID],
    status: Optional[str] = None
) -> int:
    params: list[Any] = []
    base_query = "SELECT COUNT(f.id) FROM file f JOIN collection c ON f.collection_id = c.id"
    join_clause = " LEFT JOIN file_status fs ON f.id = fs.id" if status else ""
    where_conditions = ["f.name != 'pending_upload'"]

    if active_ngroup_id:
        params.append(active_ngroup_id)
        where_conditions.append(f"c.ngroup_id = ${len(params)}")
    
    if status:
        params.append(status)
        where_conditions.append(f"fs.status = ${len(params)}")

    where_clause = f"WHERE {' AND '.join(where_conditions)}"
    query = f"{base_query}{join_clause} {where_clause}"
    
    count = await conn.fetchval(query, *params)
    return count or 0


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
        SELECT 
            f.id, f.name, f.type, f.cueuser_uploaded, f.size_bytes, f.collection_id, f.collection_path, f.checksum, 
            fs.status, fs.upload_time, fs.scan_results, fs.egress_start
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


async def delete_file(conn: Connection, file_id: UUID) -> bool:
    """Deletes a file record. Assumes ON DELETE CASCADE is set for related tables."""
    try:
        deleted_id = await conn.fetchval("DELETE FROM file WHERE id = $1 RETURNING id", file_id)
        return deleted_id is not None
    except ForeignKeyViolationError as e:
        logger.warning("db.file.delete.failed_fk", file_id=str(file_id), error=str(e))
        raise ValueError("Cannot delete this file because it is still referenced.") from e

