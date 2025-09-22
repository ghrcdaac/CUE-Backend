# File: src/python/api/v2/utils/file.py

from uuid import UUID
from typing import List, Dict, Any, Tuple, Optional
from v2.type_util.auth import AuthUser
import structlog
from fastapi import Request
import json

from v2.database_util import file as file_db
from v2.type_util.file import FileUpdateRequest

logger = structlog.get_logger(__name__)

class FileNotFoundError(Exception):
    pass

def _process_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to parse JSON fields from a database record."""
    if record and record.get('scan_results') and isinstance(record['scan_results'], str):
        try:
            record['scan_results'] = json.loads(record['scan_results'])
        except json.JSONDecodeError:
            logger.warning("file.process.json_decode_error", file_id=record.get('id'))
            record['scan_results'] = {"error": "Invalid JSON in database"}
    return record

async def get_file_details(request: Request, file_id: UUID) -> Dict[str, Any]:
    """Retrieves full details for a single file."""
    async with request.state.pool.acquire() as conn:
        file_data = await file_db.get_file_details(conn, file_id)
    if not file_data:
        raise FileNotFoundError(f"File not found with ID: {file_id}")
    return _process_record(dict(file_data))

async def find_files_by_name(
    request: Request,
    user: AuthUser, # Accept user object
    active_ngroup_id: Optional[str], # Accept ngroup ID
    file_name: str
) -> List[Dict[str, Any]]:
    """Finds files by name within a specific ngroup."""
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    
    async with request.state.pool.acquire() as conn:
        # Call the new, more powerful database function
        records = await file_db.find_files_by_name(
            conn,
            requesting_user=user.model_dump(),
            active_ngroup_id=ngroup_id_to_filter,
            file_name=file_name
        )
    return [_process_record(dict(r)) for r in records]

async def list_files(
    request: Request,
    user: AuthUser, # Accept user object
    active_ngroup_id: Optional[str], # Accept ngroup ID
    page: int,
    page_size: int,
    status: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieves a paginated list of files for a specific ngroup, optionally by status."""
    offset = (page - 1) * page_size
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    
    async with request.state.pool.acquire() as conn:
        # Pass user and ngroup ID to both database functions
        user_dump = user.model_dump()
        total = await file_db.count_files_for_ngroup(
            conn,
            requesting_user=user_dump,
            active_ngroup_id=ngroup_id_to_filter,
            status=status
        )
        files = await file_db.list_files_paginated(
            conn,
            requesting_user=user_dump,
            active_ngroup_id=ngroup_id_to_filter,
            limit=page_size,
            offset=offset,
            status=status
        )
    return [_process_record(dict(f)) for f in files], total

async def update_file(request: Request, file_id: UUID, file_update: FileUpdateRequest) -> Dict[str, Any]:
    """Updates a file's descriptive metadata."""
    update_data = file_update.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    
    async with request.state.pool.acquire() as conn:
        async with conn.transaction():
            success = await file_db.update_file(conn, file_id, update_data)
            if not success:
                raise FileNotFoundError(f"File not found with ID: {file_id}")
            # Fetch the updated record to return the full object
            updated_file_data = await file_db.get_file_details(conn, file_id)

    logger.info("file.updated", file_id=str(file_id), changes=update_data)
    return _process_record(dict(updated_file_data))

async def delete_file(request: Request, file_id: UUID):
    """Deletes a file record."""
    async with request.state.pool.acquire() as conn:
        success = await file_db.delete_file(conn, file_id)
    if not success:
        raise FileNotFoundError(f"File not found with ID: {file_id}")
    logger.info("file.deleted", file_id=str(file_id))