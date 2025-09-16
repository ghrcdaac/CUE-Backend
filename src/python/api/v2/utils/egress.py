# ==============================================================================
# File: src/python/api/v2/utils/egress.py

# ==============================================================================
from uuid import UUID
from typing import List, Dict, Any
import structlog
from fastapi import Request
import json

from v2.database_util import egress as egress_db
from v2.type_util.egress import EgressCreate, EgressUpdate

logger = structlog.get_logger(__name__)

class EgressNotFoundError(Exception):
    """Custom exception raised when an egress target is not found."""
    pass

def _process_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to parse the config field if it's a string."""
    if record and record.get('config') and isinstance(record['config'], str):
        record['config'] = json.loads(record['config'])
    return record

async def create_egress(request: Request, egress: EgressCreate, ngroup_id: UUID) -> Dict[str, Any]:
    """Creates a new egress record."""
    async with request.state.pool.acquire() as conn:
        new_egress = await egress_db.create_egress(
            conn, egress.type, egress.path, egress.config, ngroup_id
        )
    logger.info("egress.created", egress_id=str(new_egress['id']))
    # --- Parse the record returned from the database ---
    return _process_record(dict(new_egress))

async def get_egress(request: Request, egress_id: UUID) -> Dict[str, Any]:
    """Retrieves an egress record by its ID."""
    async with request.state.pool.acquire() as conn:
        egress = await egress_db.get_egress_by_id(conn, egress_id)
    if not egress:
        raise EgressNotFoundError(f"Egress target not found with ID: {egress_id}")
    return _process_record(dict(egress))

async def list_egresses(request: Request, ngroup_id: UUID) -> List[Dict[str, Any]]:
    """Retrieves all egress records for a specific ngroup."""
    async with request.state.pool.acquire() as conn:
        records = await egress_db.list_egresses_by_ngroup(conn, ngroup_id)
    return [_process_record(dict(r)) for r in records]

async def update_egress(request: Request, egress_id: UUID, egress_update: EgressUpdate) -> Dict[str, Any]:
    """Updates an existing egress record."""
    update_data = egress_update.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    
    async with request.state.pool.acquire() as conn:
        updated_egress = await egress_db.update_egress(conn, egress_id, update_data)
    
    if not updated_egress:
        raise EgressNotFoundError(f"Egress target not found with ID: {egress_id}")
    
    logger.info("egress.updated", egress_id=str(egress_id))
    # --- Parse the record returned from the database ---
    return _process_record(dict(updated_egress))

async def delete_egress(request: Request, egress_id: UUID):
    """Deletes an egress record by its ID."""
    async with request.state.pool.acquire() as conn:
        success = await egress_db.delete_egress(conn, egress_id)
    if not success:
        raise EgressNotFoundError(f"Egress target not found with ID: {egress_id}")
    logger.info("egress.deleted", egress_id=str(egress_id))