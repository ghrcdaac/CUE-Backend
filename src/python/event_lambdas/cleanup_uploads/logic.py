from typing import Dict, Any, List
from uuid import UUID 
import asyncpg
from model import CleanupPayload
from pydantic import ValidationError
from db import get_upload_files, delete_upload_files
import structlog

logger = structlog.get_logger(__name__)

async def validate_cleanup_event(event:Dict[str, Any]):
    try: 
        valid_cleanup_payload = CleanupPayload(**event)
    except ValidationError as e: 
        logger.info('cleanup_payload.invalid', exc_info=True)
        raise e

    return valid_cleanup_payload

async def get_upload_status_files(pool: asyncpg.Pool, payload:CleanupPayload):
    try:
        if payload.detail_type == "CleanupAllPendingUploads":
            filters_dict = {}
        else:
            # payload.detail_type == "CleanupTargetedUploads"
            if payload.query_parameters:
                filters_dict = payload.query_parameters.model_dump()
            else:
                logger.info("query_parameters.missing.required_for_targeted_cleanup")
                raise ValueError('"detail-type":"CleanupTargetedUploads", payload missing query_parameters."')

        async with pool.acquire() as conn:
            files = await get_upload_files(conn, filters_dict)
        logger.info("upload_status_files.retrieved.success", files=files, total=len(files))
    except Exception as e:
        logger.error('upload_status_files.retrieve.failed', filters=filters_dict, error=e)
        raise e

    return files


async def delete_upload_status_files(pool: asyncpg.Pool, files:List[UUID]):
    try:    
        async with pool.acquire() as conn:
            success = await delete_upload_files(conn, files)
    except Exception as e:
        logger.error('upload_status_files.delete.failed', files=files, error=e)
        raise e

    return success