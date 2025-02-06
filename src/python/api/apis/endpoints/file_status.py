from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from typing import List

from utils.file_status import (create_file_status,
                                    delete_file_status,
                                    get_file_status,
                                    list_file_statuses,
                                    FileStatusNotFoundError, update_file_status)
from lambda_utils.type_util.file_status import (FileStatusCreate,
                                               FileStatusReturn,
                                               FileStatusUpdate)

router = APIRouter(prefix="/file_status", tags=["file_status"])

@router.post("/", response_model=FileStatusReturn)
async def create_file_status_endpoint(file_status: FileStatusCreate):
    try:
        return await create_file_status(file_status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{id}", response_model=FileStatusReturn)  
async def get_file_status_endpoint(id: UUID): 
    try:
        file_status = await get_file_status(id)  
        return file_status
    except FileStatusNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{id}", response_model=FileStatusReturn)  
async def update_file_status_endpoint(id: UUID, file_status_update: FileStatusUpdate): 
    try:
        updated_file_status = await update_file_status(id, file_status_update)  
        return updated_file_status
    except FileStatusNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", response_model=bool)  
async def delete_file_status_endpoint(id: UUID):  
    try:
        success = await delete_file_status(id)  
        return success
    except FileStatusNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[FileStatusReturn])
async def list_file_statuses_endpoint():
    try:
        return await list_file_statuses()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))