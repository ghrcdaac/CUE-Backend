# ==============================================================================
# File: src/python/api/v2/utils/ngroup.py (Updated)
# --- MODIFIED to use the shared connection pool from the request state ---
# ==============================================================================
from uuid import UUID
from typing import List, Optional, Dict, Any
import structlog
from fastapi import Request # <-- Import Request

# --- REMOVED: from core.db import get_db_connection ---
from v2.database_util import ngroup as ngroup_db
from v2.type_util.ngroup import NgroupCreate, NgroupUpdate

logger = structlog.get_logger(__name__)

class NgroupNotFoundError(Exception):
    """Custom exception raised when an ngroup is not found."""
    def __init__(self, ngroup_id: UUID):
        self.ngroup_id = ngroup_id
        super().__init__(f"Ngroup not found with ID: {ngroup_id}")

# --- MODIFIED: Functions now accept the `request` object ---

async def create_ngroup(request: Request, ngroup: NgroupCreate) -> Dict[str, Any]:
    """Creates a new ngroup record."""
    async with request.state.pool.acquire() as conn:
        new_ngroup = await ngroup_db.create_ngroup(conn, ngroup.short_name, ngroup.long_name)
    logger.info("ngroup.created", ngroup_id=str(new_ngroup['id']))
    return dict(new_ngroup)

async def get_ngroup(request: Request, ngroup_id: UUID) -> Dict[str, Any]:
    """Retrieves an ngroup record by its ID."""
    async with request.state.pool.acquire() as conn:
        ngroup = await ngroup_db.get_ngroup_by_id(conn, ngroup_id)
    if not ngroup:
        raise NgroupNotFoundError(ngroup_id=ngroup_id)
    return dict(ngroup)

async def update_ngroup(request: Request, ngroup_id: UUID, ngroup_update: NgroupUpdate) -> Dict[str, Any]:
    """Updates an existing ngroup record."""
    update_data = ngroup_update.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    
    async with request.state.pool.acquire() as conn:
        updated_ngroup = await ngroup_db.update_ngroup(conn, ngroup_id, update_data)
    
    if not updated_ngroup:
        raise NgroupNotFoundError(ngroup_id=ngroup_id)
    
    logger.info("ngroup.updated", ngroup_id=str(ngroup_id))
    return dict(updated_ngroup)

async def delete_ngroup(request: Request, ngroup_id: UUID):
    """Deletes an ngroup record by its ID."""
    async with request.state.pool.acquire() as conn:
        success = await ngroup_db.delete_ngroup(conn, ngroup_id)
    if not success:
        raise NgroupNotFoundError(ngroup_id=ngroup_id)
    logger.info("ngroup.deleted", ngroup_id=str(ngroup_id))

async def list_ngroups(request: Request) -> List[Dict[str, Any]]:
    """Retrieves all ngroup records."""
    async with request.state.pool.acquire() as conn:
        records = await ngroup_db.list_ngroups(conn)
    return [dict(r) for r in records]

async def list_ngroups_for_form(request: Request) -> List[Dict[str, Any]]:
    """Retrieves a simplified list of ngroups for forms."""
    async with request.state.pool.acquire() as conn:
        records = await ngroup_db.list_ngroups_for_form(conn)
    return [dict(r) for r in records]
