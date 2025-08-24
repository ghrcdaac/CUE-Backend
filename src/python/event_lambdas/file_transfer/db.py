from typing import List, Dict, Any, Optional
from uuid import UUID
from asyncpg import Connection
import os 
import json
import logging

logger = logging.getLogger(__file__)
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))

async def fetch_destinations(conn:Connection, collection_ids:List[UUID]) -> Optional[Dict[UUID,Any]]:
    query = """
        SELECT c.id as collection_id, e.path as path, e.config as config
        FROM collection c JOIN egress e ON c.egress_id = e.id
        WHERE e.type = 's3' AND c.id = ANY($1::UUID[])
    """
    try:
        records = await conn.fetch(query, collection_ids)
        if not records:
            logger.warning("No egress records retrieved")
            return None
        destinations = {}
        for record in records:
            key = record["collection_id"]
            destinations[key] = {"path": record["path"],
                                 "config": json.loads((record["config"]))}
        logger.info("Found egress information")
        logger.info(destinations)
        return destinations
    except Exception as e:
        logger.error(f"Error fetching egress information:{e}", exc_info=True)
        raise


async def fetch_file_metadata(conn:Connection, file_ids:List[UUID]) -> Optional[Dict[UUID, Any]]:
    query = """
        SELECT id as file_id, collection_path, collection_id, name
        FROM file
        WHERE id = ANY($1::UUID[])
    """
    try:
        records = await conn.fetch(query, file_ids)
        if not records:
            logger.warning("No file metadata retrieved")
            return None
        file_metadata = {}
        for record in records:
            key = record["file_id"]
            file_metadata[key] = {"collection_path": record["collection_path"],
                                  "collection_id": record["collection_id"],
                                  "name": record["name"]}
        logger.info("Found file metadata")
        logger.info(file_metadata)
        return file_metadata
    except Exception as e:
        logger.error(f"Error fetching file_metadata:{e}", exc_info=True)
        raise


async def update_status_distributed(conn:Connection, file_ids:List[UUID]) -> bool:
    query = """
        UPDATE file_status
        SET status = $1, egress_start = NOW()
        WHERE id = ANY($2::UUID[]) 
    """
    try:
        result = await conn.execute(query, *("distributed", file_ids))
        if result.startswith('UPDATE'):
            #rows = int(result.split()[1])
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating file statuses: {e}", exc_info=True)
        raise
