# ==============================================================================
# File: src/python/api/v2/database_util/ngroup.py
# Purpose: Contains all raw SQL queries for ngroup management.
# Change: Added specific exception handling for database errors.
# ==============================================================================
from asyncpg import Connection, DataError, UniqueViolationError
from typing import List, Optional, Dict, Any
from uuid import UUID
import structlog

logger = structlog.get_logger(__name__)

async def create_ngroup(conn: Connection, short_name: str, long_name: str) -> Dict[str, Any]:
    """Inserts a new ngroup record into the database."""
    query = """
        INSERT INTO ngroup (short_name, long_name)
        VALUES ($1, $2)
        RETURNING id, short_name, long_name;
    """
    try:
        return await conn.fetchrow(query, short_name, long_name)
    except UniqueViolationError as e:
        logger.error("db.ngroup.create.failed_unique", error=str(e))
        raise ValueError("A ngroup with the same short_name or long_name already exists.") from e
    except DataError as e:
        logger.error("db.ngroup.create.failed_data_error", error=str(e))
        raise ValueError("Invalid data provided for creating an ngroup.") from e

async def get_ngroup_by_id(conn: Connection, ngroup_id: UUID) -> Optional[Dict[str, Any]]:
    """Retrieves an ngroup record from the database by its ID."""
    return await conn.fetchrow("SELECT id, short_name, long_name FROM ngroup WHERE id = $1", ngroup_id)

async def update_ngroup(conn: Connection, ngroup_id: UUID, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Updates an existing ngroup record in the database."""
    fields, values = list(update_data.keys()), list(update_data.values())
    set_clause = ", ".join(f"{field} = ${i+1}" for i, field in enumerate(fields))
    query = f"UPDATE ngroup SET {set_clause} WHERE id = ${len(fields) + 1} RETURNING id, short_name, long_name;"
    
    try:
        return await conn.fetchrow(query, *values, ngroup_id)
    except UniqueViolationError as e:
        logger.error("db.ngroup.update.failed_unique", error=str(e))
        raise ValueError("A ngroup with the same short_name or long_name already exists.") from e

async def delete_ngroup(conn: Connection, ngroup_id: UUID) -> bool:
    """Deletes an ngroup record from the database by its ID."""
    result = await conn.execute("DELETE FROM ngroup WHERE id = $1", ngroup_id)
    return result.strip() == "DELETE 1"

async def list_ngroups(conn: Connection) -> List[Dict[str, Any]]:
    """Retrieves all ngroup records from the database."""
    return await conn.fetch("SELECT id, short_name, long_name FROM ngroup ORDER BY short_name;")

async def list_ngroups_for_form(conn: Connection) -> List[Dict[str, Any]]:
    """Retrieves a simplified list of ngroups (id, short_name) for forms."""
    return await conn.fetch("SELECT id, short_name FROM ngroup ORDER BY short_name;")

async def list_all_ngroup_ids(conn: Connection) -> List[UUID]:
    """
    Fetches a list of all ngroup IDs from the database.
    This is used when creating a security user to grant them access to all groups.
    """
    records = await conn.fetch("SELECT id FROM ngroup;")
    return [record['id'] for record in records]