# File: src/python/api/v2/utils/file.py

from uuid import UUID
from typing import List, Dict, Any, Tuple, Optional
from v2.type_util.auth import AuthUser
import structlog
from fastapi import Request, HTTPException, status
import json
import hashlib

from v2.database_util import file as file_db
from v2.database_util import api_keys as api_key_db
from v2.type_util.file import FileUpdateRequest, FileListRequest 
from datetime import date

logger = structlog.get_logger(__name__)

class FileNotFoundError(Exception):
    pass
class ApiKeyError(Exception):
    """Base exception for API key validation errors."""
    pass

class InvalidApiKeyError(ApiKeyError):
    """Raised when the API key is not found or invalid."""
    pass

class ApiKeyScopeError(ApiKeyError):
    """Raised when the API key lacks the required scope."""
    pass

class ApiKeyConfigurationError(ApiKeyError):
    """Raised when the key is misconfigured (e.g., no group)."""
    pass

class FileAccessError(Exception):
    """Raised when a file cannot be found or accessed by the user."""
    pass


def _process_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper to parse JSON fields and normalize scan_results to always be an array.
    """
    if not record:
        return None
    processed_record = dict(record)
    scan_results = processed_record.get('scan_results')
    
    if scan_results and isinstance(scan_results, str):
        try:
            scan_results = json.loads(scan_results)
        except json.JSONDecodeError:
            logger.warning("file.process.json_decode_error", file_id=processed_record.get('id'))
            scan_results = [{"error": "Invalid JSON in database"}]
    
    if isinstance(scan_results, dict):
        processed_record['scan_results'] = [scan_results]
    elif isinstance(scan_results, list):
        processed_record['scan_results'] = scan_results
    else:
        processed_record['scan_results'] = None

    collection_name = processed_record.pop('collection_name', None)
    if collection_name:
        processed_record['collection'] = {
            'id': processed_record.get('collection_id'),
            'name': collection_name
        }
        
    return processed_record

async def get_file_details(request: Request, file_id: UUID) -> Dict[str, Any]:
    async with request.state.pool.acquire() as conn:
        file_data = await file_db.get_file_details(conn, file_id)
    if not file_data:
        raise FileNotFoundError(f"File not found with ID: {file_id}")
    return _process_record(file_data)

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

async def search_files_by_name(
    request: Request,
    user: AuthUser,
    active_ngroup_id: Optional[str],
    partial_file_name: str,
    page: int,
    page_size: int,
    status: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], bool]:
    """Searches files by partial name within a specific ngroup, optionally by status."""
    offset = (page - 1) * page_size
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None

    async with request.state.pool.acquire() as conn:
        user_dump = user.model_dump()
        records = await file_db.search_files_by_name(
            conn,
            requesting_user=user_dump,
            active_ngroup_id=ngroup_id_to_filter,
            partial_file_name=partial_file_name,
            limit=page_size + 1,
            offset=offset,
            status=status
        )
    has_more = len(records) > page_size
    return [_process_record(dict(r)) for r in records[:page_size]], has_more

async def list_files(
    request: Request,
    user: AuthUser,
    active_ngroup_id: Optional[str],
    page: int,
    page_size: int,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieves a paginated list of files for a specific ngroup, optionally by status."""
    offset = (page - 1) * page_size
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    
    async with request.state.pool.acquire() as conn:
        user_dump = user.model_dump()
        total = await file_db.count_files_for_ngroup(
            conn,
            requesting_user=user_dump,
            active_ngroup_id=ngroup_id_to_filter,
            status=status,
            start_date=start_date,
            end_date=end_date
        )
        files = await file_db.list_files_paginated(
            conn,
            requesting_user=user_dump,
            active_ngroup_id=ngroup_id_to_filter,
            limit=page_size,
            offset=offset,
            status=status,
            start_date=start_date,
            end_date=end_date
        )
    return [_process_record(f) for f in files], total

async def list_files_by_api_key(
    request: Request,
    body: FileListRequest
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Validates an API key and fetches files. 
    If file_ids are provided, filters by them.
    If status/dates are provided, filters by them.
    All filters are additive (AND logic).
    """
    
    api_key = body.apiKey
    if not api_key or not api_key.startswith("cue_sk_"):
        raise InvalidApiKeyError("A valid application API key is required.")

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    async with request.state.pool.acquire() as conn:
        key_data = await api_key_db.get_user_from_api_key(conn, key_hash)

    if not key_data:
        raise InvalidApiKeyError("Invalid API Key")

    if "file:read" not in key_data.get("scopes", []):
        raise ApiKeyScopeError("API Key lacks required scope 'file:read'")
    
    ngroup_id_to_filter = key_data.get("ngroup_id")
    if not ngroup_id_to_filter:
        raise ApiKeyConfigurationError("API Key is not associated with a group.")

    async with request.state.pool.acquire() as conn:
        offset = (body.page - 1) * body.page_size
        proxy_user_for_db = {"roles": ["proxy"]}
                
        total = await file_db.count_files_for_ngroup(
            conn, 
            requesting_user=proxy_user_for_db, 
            active_ngroup_id=ngroup_id_to_filter, 
            status=body.status, 
            start_date=body.start_date, 
            end_date=body.end_date,
            file_ids=body.file_ids 
        )
        
        files = await file_db.list_files_paginated(
            conn, 
            requesting_user=proxy_user_for_db, 
            active_ngroup_id=ngroup_id_to_filter, 
            limit=body.page_size, 
            offset=offset, 
            status=body.status, 
            start_date=body.start_date, 
            end_date=body.end_date,
            file_ids=body.file_ids
        )
        
        return [_process_record(f) for f in files], total


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
            updated_file_data = await file_db.get_file_details(conn, file_id)

    logger.info("file.updated", file_id=str(file_id), changes=update_data)
    return _process_record(updated_file_data)

async def delete_file(request: Request, file_id: UUID):
    """Deletes a file record."""
    async with request.state.pool.acquire() as conn:
        success = await file_db.delete_file(conn, file_id)
    if not success:
        raise FileNotFoundError(f"File not found with ID: {file_id}")
    logger.info("file.deleted", file_id=str(file_id))
