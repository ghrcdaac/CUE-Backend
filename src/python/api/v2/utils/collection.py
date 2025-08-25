# File: src/python/api/v2/utils/collection.py

from uuid import UUID
from typing import List, Dict, Any
import structlog

from core.db import get_db_connection
from v2.database_util import collection as collection_db
# New dependencies for validation
from v2.database_util import provider as provider_db
from v2.database_util import egress as egress_db
from v2.type_util.collection import CollectionCreate, CollectionUpdate

logger = structlog.get_logger(__name__)

class CollectionNotFoundError(Exception):
    """Custom exception raised when a collection is not found."""
    pass

async def create_collection(collection: CollectionCreate, ngroup_id: UUID) -> Dict[str, Any]:
    """Creates a new collection record after validating dependencies."""
    async with get_db_connection() as conn:
        # --- START: New Validation Logic ---
        provider = await provider_db.get_provider_by_id(conn, collection.provider_id)
        if not provider or provider['ngroup_id'] != ngroup_id:
            raise ValueError(f"Provider with ID '{collection.provider_id}' not found in this ngroup.")

        egress = await egress_db.get_egress_by_id(conn, collection.egress_id)
        if not egress or egress['ngroup_id'] != ngroup_id:
            raise ValueError(f"Egress target with ID '{collection.egress_id}' not found in this ngroup.")
        # --- END: New Validation Logic ---

        new_collection = await collection_db.create_collection(
            conn, collection.short_name, collection.active, ngroup_id, collection.provider_id, collection.egress_id
        )
    logger.info("collection.created", collection_id=str(new_collection['id']))
    return dict(new_collection)

async def get_collection(collection_id: UUID) -> Dict[str, Any]:
    """Retrieves a collection record by its ID."""
    async with get_db_connection() as conn:
        collection = await collection_db.get_collection_by_id(conn, collection_id)
    if not collection:
        raise CollectionNotFoundError(f"Collection not found with ID: {collection_id}")
    return dict(collection)

async def list_collections(ngroup_id: UUID) -> List[Dict[str, Any]]:
    """Retrieves all collection records for a specific ngroup."""
    async with get_db_connection() as conn:
        records = await collection_db.list_collections_by_ngroup(conn, ngroup_id)
    return [dict(r) for r in records]

async def update_collection(collection_id: UUID, collection_update: CollectionUpdate) -> Dict[str, Any]:
    """Updates an existing collection record."""
    update_data = collection_update.model_dump(exclude_unset=True)
    if not update_data:
        raise ValueError("No update data provided.")
    
    async with get_db_connection() as conn:
        # If provider or egress are being changed, they must be re-validated
        if 'provider_id' in update_data or 'egress_id' in update_data:
            current_collection = await get_collection(collection_id)
            ngroup_id = current_collection['ngroup_id']

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

async def delete_collection(collection_id: UUID):
    """Deletes a collection record by its ID."""
    async with get_db_connection() as conn:
        success = await collection_db.delete_collection(conn, collection_id)
    if not success:
        raise CollectionNotFoundError(f"Collection not found with ID: {collection_id}")
    logger.info("collection.deleted", collection_id=str(collection_id))