# ==============================================================================
# File: src/python/api/v2/utils/file.py (Updated)
# --- MODIFIED to use the shared connection pool from the request state ---
# ==============================================================================
from uuid import UUID
from typing import List, Dict, Any, Tuple
import structlog
from fastapi import Request # <-- Import Request

# --- REMOVED: from core.db import get_db_connection ---
from v2.database_util import file as file_db
from v2.type_util.file import FileUpdateRequest

logger = structlog.get_logger(__name__)

class FileNotFoundError(Exception):
    pass

# --- MODIFIED: Functions now accept the `request` object ---

async def get_file_details(request: Request, file_id: UUID) -> Dict[str, Any]:
    """Retrieves full details for a single file."""
    async with request.state.pool.acquire() as conn:
        file_data = await file_db.get_file_details(conn, file_id)
    if not file_data:
        raise FileNotFoundError(f"File not found with ID: {file_id}")
    return dict(file_data)

async def list_files(request: Request, ngroup_id: UUID, page: int, page_size: int) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieves a paginated list of files for a specific ngroup."""
    offset = (page - 1) * page_size
    async with request.state.pool.acquire() as conn:
        total_count = await file_db.count_files_for_ngroup(conn, ngroup_id)
        files = await file_db.list_files_paginated(conn, ngroup_id, page_size, offset)
    return [dict(f) for f in files], total_count

async def update_file(request: Request, file_id: UUID, file_update: FileUpdateRequest) -> Dict[str, Any]:
    """Updates a file's descriptive metadata."""
    update_data = file_update.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    
    async with request.state.pool.acquire() as conn:
        success = await file_db.update_file(conn, file_id, update_data)
        if not success:
            raise FileNotFoundError(f"File not found with ID: {file_id}")
        
        # Fetch the updated record to return the full object
        updated_file_data = await file_db.get_file_details(conn, file_id)

    logger.info("file.updated", file_id=str(file_id), changes=update_data)
    return dict(updated_file_data)

async def delete_file(request: Request, file_id: UUID):
    """Deletes a file record."""
    async with request.state.pool.acquire() as conn:
        success = await file_db.delete_file(conn, file_id)
    if not success:
        raise FileNotFoundError(f"File not found with ID: {file_id}")
    logger.info("file.deleted", file_id=str(file_id))
