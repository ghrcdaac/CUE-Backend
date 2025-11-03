# ==============================================================================
# File: src/python/api/v2/utils/collection.py (Updated)
# --- MODIFIED to use the shared connection pool from the request state ---
# ==============================================================================
from uuid import UUID
from typing import List, Dict, Any, Optional
import structlog
from fastapi import Request 
from v2.database_util import collection as collection_db
from v2.database_util import provider as provider_db
from v2.database_util import egress as egress_db
from v2.type_util.collection import CollectionCreate, CollectionUpdate
from v2.type_util.auth import AuthUser

logger = structlog.get_logger(__name__)

class CollectionNotFoundError(Exception):
    """Custom exception raised when a collection is not found."""
    pass

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

async def list_collections(
    request: Request,
    user: AuthUser, # Accept the full user object for role checks
    active_ngroup_id: Optional[str] # Accept the optional ngroup ID string
) -> List[Dict[str, Any]]:
    """Retrieves all collection records based on the user's roles and active ngroup."""
    
    # Convert string UUID from header to UUID object, or None
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None
    
    async with request.state.pool.acquire() as conn:
        records = await collection_db.list_collections(
            conn, 
            requesting_user=user.model_dump(),
            active_ngroup_id=ngroup_id_to_filter
        )
    return [dict(r) for r in records]


async def update_collection(
    request: Request, 
    collection_id: UUID, 
    collection_update: CollectionUpdate,
    current_collection: Dict[str, Any] 
) -> Dict[str, Any]:
    """Updates an existing collection record."""
    update_data = collection_update.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    
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
