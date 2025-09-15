# ==============================================================================
# File: src/python/api/v2/utils/role.py (Updated)
# --- MODIFIED to use the shared connection pool from the request state ---
# ==============================================================================
from uuid import UUID
from typing import List, Optional, Dict, Any
import structlog
from fastapi import Request # <-- Import Request

# --- REMOVED: from core.db import get_db_connection ---
from v2.database_util import role as role_db
from v2.type_util.role import RoleCreate, RoleUpdate

logger = structlog.get_logger(__name__)

class RoleNotFoundError(Exception):
    """Custom exception raised when a role is not found."""
    def __init__(self, identifier: Any):
        super().__init__(f"Role not found with identifier: {identifier}")

# --- MODIFIED: Functions now accept the `request` object ---

async def create_role(request: Request, role: RoleCreate) -> Dict[str, Any]:
    """Creates a new role record."""
    async with request.state.pool.acquire() as conn:
        new_role = await role_db.create_role(conn, role.short_name, role.long_name)
    logger.info("role.created", role_id=str(new_role['id']))
    return dict(new_role)

async def get_role(request: Request, role_id: UUID) -> Dict[str, Any]:
    """Retrieves a role record by its ID."""
    async with request.state.pool.acquire() as conn:
        role = await role_db.get_role_by_id(conn, role_id)
    if not role:
        raise RoleNotFoundError(identifier=role_id)
    return dict(role)

async def get_role_by_lookup(request: Request, short_name: Optional[str], long_name: Optional[str]) -> Dict[str, Any]:
    """Retrieves a role by its short or long name."""
    if not short_name and not long_name:
        raise ValueError("Either short_name or long_name must be provided.")
    
    async with request.state.pool.acquire() as conn:
        role = await role_db.get_role_by_lookup(conn, short_name=short_name, long_name=long_name)
    
    if not role:
        identifier = short_name or long_name
        raise RoleNotFoundError(identifier=identifier)
    return dict(role)

async def list_roles(request: Request) -> List[Dict[str, Any]]:
    """Retrieves all role records."""
    async with request.state.pool.acquire() as conn:
        records = await role_db.list_roles(conn)
    return [dict(r) for r in records]

async def update_role(request: Request, role_id: UUID, role_update: RoleUpdate) -> Dict[str, Any]:
    """Updates an existing role record."""
    update_data = role_update.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    
    async with request.state.pool.acquire() as conn:
        updated_role = await role_db.update_role(conn, role_id, update_data)
    
    if not updated_role:
        raise RoleNotFoundError(identifier=role_id)
    
    logger.info("role.updated", role_id=str(role_id))
    return dict(updated_role)

async def delete_role(request: Request, role_id: UUID):
    """Deletes a role record by its ID."""
    async with request.state.pool.acquire() as conn:
        success = await role_db.delete_role(conn, role_id)
    if not success:
        raise RoleNotFoundError(identifier=role_id)
    logger.info("role.deleted", role_id=str(role_id))
