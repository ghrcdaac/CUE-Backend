# ==============================================================================
# File: src/python/api/v2/utils/collection.py (Updated)
# --- MODIFIED to use the shared connection pool from the request state ---
# ==============================================================================
from uuid import UUID
from typing import List, Dict, Any, Tuple
import structlog
from fastapi import Request # <-- Import Request

# --- REMOVED: from core.db import get_db_connection ---
from v2.database_util import collection as collection_db
from v2.database_util import provider as provider_db
from v2.database_util import egress as egress_db
from v2.type_util.collection import CollectionCreate, CollectionUpdate

logger = structlog.get_logger(__name__)

class CollectionNotFoundError(Exception):
    """Custom exception raised when a collection is not found."""
    pass

# --- MODIFIED: Functions now accept the `request` object ---

async def create_collection(request: Request, collection: CollectionCreate, ngroup_id: UUID) -> Dict[str, Any]:
    """Creates a new collection record after validating dependencies."""
    async with request.state.pool.acquire() as conn:
        provider = await provider_db.get_provider_by_id(conn, collection.provider_id)
        if not provider or provider['ngroup_id'] != ngroup_id:
            raise ValueError(f"Provider with ID '{collection.provider_id}' not found in this ngroup.")

        egress = await egress_db.get_egress_by_id(conn, collection.egress_id)
        if not egress or egress['ngroup_id'] != ngroup_id:
            raise ValueError(f"Egress target with ID '{collection.egress_id}' not found in this ngroup.")

        new_collection = await collection_db.create_collection(
            conn, collection.short_name, collection.active, ngroup_id, collection.provider_id, collection.egress_id
        )
    logger.info("collection.created", collection_id=str(new_collection['id']))
    return dict(new_collection)

async def get_collection(request: Request, collection_id: UUID) -> Dict[str, Any]:
    """Retrieves a collection record by its ID."""
    async with request.state.pool.acquire() as conn:
        collection = await collection_db.get_collection_by_id(conn, collection_id)
    if not collection:
        raise CollectionNotFoundError(f"Collection not found with ID: {collection_id}")
    return dict(collection)

async def list_collections(request: Request, ngroup_id: UUID,  page:int, page_size:int) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieves all collection records for a specific ngroup."""
    async with request.state.pool.acquire() as conn:
        params = (ngroup_id,)
        offset = (page - 1) * page_size
        params = (ngroup_id, page_size, offset)
        total_count = await collection_db.get_collection_count(conn, ngroup_id);
        result = []
        if total_count > 0:
            records = await collection_db.list_collections_by_ngroup(conn, params)
            result = [dict(r) for r in records]
    return result,total_count

async def update_collection(request: Request, collection_id: UUID, collection_update: CollectionUpdate) -> Dict[str, Any]:
    """Updates an existing collection record."""
    update_data = collection_update.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    
    # This internal call must also be updated to pass the request object
    current_collection = await get_collection(request, collection_id)
    ngroup_id = current_collection['ngroup_id']
    
    async with request.state.pool.acquire() as conn:
        if 'provider_id' in update_data:
            provider = await provider_db.get_provider_by_id(conn, update_data['provider_id'])
            if not provider or provider['ngroup_id'] != ngroup_id:
                raise ValueError(f"Provider with ID '{update_data['provider_id']}' not found in this ngroup.")
        
        if 'egress_id' in update_data:
            egress = await egress_db.get_egress_by_id(conn, update_data['egress_id'])
            if not egress or egress['ngroup_id'] != ngroup_id:
                raise ValueError(f"Egress target with ID '{update_data['egress_id']}' not found in this ngroup.")

        updated_collection = await collection_db.update_collection(conn, collection_id, update_data)
    
    if not updated_collection:
        raise CollectionNotFoundError(f"Collection not found with ID: {collection_id}")
    
    logger.info("collection.updated", collection_id=str(collection_id))
    return dict(updated_collection)

async def delete_collection(request: Request, collection_id: UUID):
    """Deletes a collection record by its ID."""
    async with request.state.pool.acquire() as conn:
        success = await collection_db.delete_collection(conn, collection_id)
    if not success:
        raise CollectionNotFoundError(f"Collection not found with ID: {collection_id}")
    logger.info("collection.deleted", collection_id=str(collection_id))


