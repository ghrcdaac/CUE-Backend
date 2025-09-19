import structlog
from typing import List, Dict, Any, Optional
from uuid import UUID
import os 
import json

from asyncpg import Connection
from asyncpg.exceptions import PostgresError

logger = structlog.get_logger(__file__)

async def fetch_destinations(conn:Connection, collection_ids:List[UUID]) -> Dict[UUID, Any]:
    query = """
        SELECT c.id as collection_id, e.path as path, e.config as config
        FROM collection c JOIN egress e ON c.egress_id = e.id
        WHERE e.type = 's3' AND c.id = ANY($1::UUID[])
    """
    try:
        records = await conn.fetch(query, collection_ids)
        destinations = {}
        for record in records:
            key = record["collection_id"]
            destinations[key] = {
                "path": record["path"],
                "config": json.loads((record["config"]))
            }
        return destinations
    except PostgresError as e:
        logger.error("db.fetch_destinations.postgres_error", collection_ids=collection_ids, exc_info=True)
        raise e
    except Exception as e:
        logger.error("db.fetch_destinations.unexpected_error", collection_ids=collection_ids, exc_info=True)
        raise e


async def fetch_file_metadata(conn:Connection, file_ids:List[UUID]) -> Dict[UUID, Any]: 
    query = """
        SELECT id as file_id, collection_path, collection_id, name
        FROM file
        WHERE id = ANY($1::UUID[])
    """
    try:
        records = await conn.fetch(query, file_ids)
        file_metadata = {}
        for record in records:
            key = record["file_id"]
            file_metadata[key] = {
                "collection_path": record["collection_path"],
                "collection_id": record["collection_id"],
                "name": record["name"]
            }
        return file_metadata
    except PostgresError as e:
        logger.error("db.fetch_file_metadata.postgres_error", file_ids=file_ids, exc_info=True)
        raise
    except Exception as e:
        logger.error("db.fetch_file_metadata.unexpected_error", file_ids=file_ids, exc_info=True)
        raise


async def update_status_distributed(conn:Connection, file_ids:List[UUID]) -> bool:
    query = """
        UPDATE file_status
        SET status = $1, egress_start = NOW()
        WHERE id = ANY($2::UUID[]) 
    """
    try:
        result = await conn.execute(query, *("distributed", file_ids))
        if not result:
           logger.warning("db.update_status.failed", file_ids=file_ids)
           return False
        logger.info("db.update_status.success", file_ids=file_ids)
        return True
    except PostgresError as e:
        logger.error("db.update_status.postgres_error", file_ids=file_ids, exc_info=True)
        raise e
    except Exception as e:
        logger.error("db.update_status.unexpected_error", file_ids=file_ids, exc_info=True)
        raise e
