
    
from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from typing import List, Optional

from utils.file import create_file, get_file, update_file, delete_file, list_files, FileNotFoundError, get_files_by_name
from lambda_utils.type_util.file import FileCreate, FileReturn, FileUpdate

router = APIRouter(prefix="/file", tags=["file"])

@router.post("/", response_model=FileReturn)
async def create_file_endpoint(file: FileCreate):
    try:
        return await create_file(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/find", response_model=List[FileReturn])
async def lookup_file_endpoint(
    name: str = Query(..., description="File name to search for")
):
    try:
        files = await get_files_by_name(name)
        return files
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found with name: {name}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@router.get("/{file_id}", response_model=FileReturn)
async def get_file_endpoint(file_id: UUID):
    try:
        file = await get_file(file_id)
        return file
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{file_id}", response_model=FileReturn)
async def update_file_endpoint(file_id: UUID, file_update: FileUpdate):
    try:
        updated_file = await update_file(file_id, file_update)
        return updated_file
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{file_id}", response_model=bool)
async def delete_file_endpoint(file_id: UUID):
    try:
        success = await delete_file(file_id)
        return success
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[FileReturn])
async def list_files_endpoint():
    try:
        return await list_files()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{file_id}", response_model=FileReturn)
async def get_file_endpoint(file_id: UUID):
    try:
        file = await get_file(file_id)
        return file
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{file_id}", response_model=FileReturn)
async def update_file_endpoint(file_id: UUID, file_update: FileUpdate):
    try:
        updated_file = await update_file(file_id, file_update)
        return updated_file
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{file_id}", response_model=bool)
async def delete_file_endpoint(file_id: UUID):
    try:
        success = await delete_file(file_id)
        return success
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[FileReturn])
async def list_files_endpoint():
    try:
        return await list_files()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))