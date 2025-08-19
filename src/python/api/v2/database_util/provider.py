# ==============================================================================
# File: src/python/api/v2/database_util/provider.py (Final)
# Purpose: Contains all raw SQL queries for provider management.
# ==============================================================================
from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError
from typing import List, Optional, Dict, Any
from uuid import UUID
import structlog

logger = structlog.get_logger(__name__)

async def create_provider(conn: Connection, ngroup_id: UUID, short_name: str, long_name: str, can_upload: bool, point_of_contact: UUID) -> Dict[str, Any]:
    """Inserts a new provider record into the database."""
    query = """
        INSERT INTO provider (ngroup_id, short_name, long_name, can_upload, point_of_contact)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *;
    """
    try:
        return await conn.fetchrow(query, ngroup_id, short_name, long_name, can_upload, point_of_contact)
    except UniqueViolationError as e:
        logger.error("db.provider.create.failed_unique", error=str(e))
        raise ValueError("A provider with the same short_name or long_name already exists.") from e
    except ForeignKeyViolationError as e:
        logger.error("db.provider.create.failed_fk", error=str(e))
        raise ValueError("The specified ngroup_id or point_of_contact does not exist.") from e

async def get_provider_by_id(conn: Connection, provider_id: UUID) -> Optional[Dict[str, Any]]:
    """Retrieves a provider record from the database by its ID."""
    return await conn.fetchrow("SELECT * FROM provider WHERE id = $1", provider_id)

async def list_providers_by_ngroup(conn: Connection, ngroup_id: UUID) -> List[Dict[str, Any]]:
    """Retrieves all provider records for a specific ngroup."""
    return await conn.fetch("SELECT * FROM provider WHERE ngroup_id = $1 ORDER BY short_name", ngroup_id)

async def list_providers_for_form(conn: Connection, ngroup_id: UUID) -> List[Dict[str, Any]]:
    """Retrieves a simplified list of providers (id, short_name) for a given ngroup."""
    return await conn.fetch("SELECT id, short_name FROM provider WHERE ngroup_id = $1 ORDER BY short_name", ngroup_id)

async def update_provider(conn: Connection, provider_id: UUID, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Updates an existing provider record in the database."""
    fields, values = list(update_data.keys()), list(update_data.values())
    set_clause = ", ".join(f"{field} = ${i+1}" for i, field in enumerate(fields))
    query = f"UPDATE provider SET {set_clause} WHERE id = ${len(fields) + 1} RETURNING *;"
    
    try:
        return await conn.fetchrow(query, *values, provider_id)
    except UniqueViolationError as e:
        logger.error("db.provider.update.failed_unique", error=str(e))
        raise ValueError("A provider with the same short_name or long_name already exists.") from e
    except ForeignKeyViolationError as e:
        logger.error("db.provider.update.failed_fk", error=str(e))
        raise ValueError("The specified point_of_contact does not exist.") from e

async def delete_provider(conn: Connection, provider_id: UUID) -> bool:
    """Deletes a provider record from the database by its ID."""
    result = await conn.execute("DELETE FROM provider WHERE id = $1", provider_id)
    return result.strip() == "DELETE 1"
