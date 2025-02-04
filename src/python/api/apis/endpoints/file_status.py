from fastapi import APIRouter, HTTPException
from uuid import UUID
from typing import List

from utils.file_status import create_file_status, get_file_status, update_file_status, delete_file_status, list_file_statuses, FileStatusNotFoundError
from lambda_utils.type_util.file_status import FileStatusCreate, FileStatusReturn, FileStatusUpdate

router = APIRouter(prefix="/file_status", tags=["file_status"])

@router.post("/", response_model=FileStatusReturn)
async def create_file_status_endpoint(file_status: FileStatusCreate):
    try:
        return await create_file_status(file_status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{file_status_id}", response_model=FileStatusReturn)
async def get_file_status_endpoint(file_status_id: UUID):
    try:
        file_status = await get_file_status(file_status_id)
        return file_status
    except FileStatusNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{file_status_id}", response_model=FileStatusReturn)
async def update_file_status_endpoint(file_status_id: UUID, file_status_update: FileStatusUpdate):
    try:
        updated_file_status = await update_file_status(file_status_id, file_status_update)
        return updated_file_status
    except FileStatusNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{file_status_id}", response_model=bool)
async def delete_file_status_endpoint(file_status_id: UUID):
    try:
        success = await delete_file_status(file_status_id)
        return success
    except FileStatusNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[FileStatusReturn])
async def list_file_statuses_endpoint():
    try:
        return await list_file_statuses()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))