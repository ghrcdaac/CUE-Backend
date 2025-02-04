from fastapi import APIRouter, HTTPException, Query, Path
from uuid import UUID
from typing import List, Optional

from utils.collection import create_collection, get_collection, list_files_for_collection, update_collection, delete_collection, list_collections, CollectionNotFoundError, get_collection_by_lookup
from lambda_utils.type_util.collection import CollectionCreate, CollectionReturn, CollectionUpdate, PaginatedFiles
from lambda_utils.type_util.file import FileReturn


router = APIRouter(prefix="/collection", tags=["collection"])

@router.post("/", response_model=CollectionReturn)
async def create_collection_endpoint(collection: CollectionCreate):
    try:
        return await create_collection(collection)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/find", response_model=CollectionReturn)
async def lookup_collection_endpoint(
    short_name: str = Query(..., description="Short name of the collection to search for")
):
    try:
        collection = await get_collection_by_lookup(short_name)
        return collection
    except CollectionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Collection not found with short_name: {short_name}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{collection_id}", response_model=CollectionReturn)
async def get_collection_endpoint(collection_id: UUID):
    try:
        collection = await get_collection(collection_id)
        return collection
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{collection_id}", response_model=CollectionReturn)
async def update_collection_endpoint(collection_id: UUID, collection_update: CollectionUpdate):
    try:
        updated_collection = await update_collection(collection_id, collection_update)
        return updated_collection
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{collection_id}", response_model=bool)
async def delete_collection_endpoint(collection_id: UUID):
    try:
        success = await delete_collection(collection_id)
        return success
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[CollectionReturn])
async def list_collections_endpoint():
    try:
        return await list_collections()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{collection_id}/files", response_model=PaginatedFiles)  
async def list_files_for_collection_endpoint(
    collection_id: UUID = Path(..., description="The ID of the collection to list files from"),
    page: int = Query(1, description="Page number, starting from 1"),
    page_size: int = Query(10, description="Number of items per page")
):
    """Lists files associated with a collection."""
    try:
        files, total_count = await list_files_for_collection(collection_id, page, page_size)
        return {
            "files": files,
            "total_count": total_count
        }
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while listing files: {e}")

@router.patch("/{collection_id}/activate", response_model=CollectionReturn)
async def activate_collection_endpoint(collection_id: UUID):
    """Activates a collection."""
    try:
        return await update_collection(collection_id, CollectionUpdate(active=True))
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{collection_id}/deactivate", response_model=CollectionReturn)
async def deactivate_collection_endpoint(collection_id: UUID):
    """Deactivates a collection."""
    try:
        return await update_collection(collection_id, CollectionUpdate(active=False))
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))