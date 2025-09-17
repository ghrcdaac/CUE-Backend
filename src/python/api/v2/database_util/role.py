# ==============================================================================
# File: src/python/api/v2/database_util/role.py (Final)
# Purpose: Contains all raw SQL queries for role management.
# New: Added list_all_privileges to support granting full access to admins.
# ==============================================================================
from asyncpg import Connection, UniqueViolationError, DataError
from typing import List, Optional, Dict, Any
from uuid import UUID
import structlog

logger = structlog.get_logger(__name__)

async def create_role(conn: Connection, short_name: str, long_name: str) -> Dict[str, Any]:
    """Inserts a new role record into the database."""
    query = """
        INSERT INTO role (short_name, long_name)
        VALUES ($1, $2)
        RETURNING id, short_name, long_name;
    """
    try:
        return await conn.fetchrow(query, short_name, long_name)
    except UniqueViolationError as e:
        logger.error("db.role.create.failed_unique", error=str(e))
        raise ValueError("A role with the same short_name or long_name already exists.") from e
    except DataError as e:
        logger.error("db.role.create.failed_data_error", error=str(e))
        raise ValueError("Invalid data provided for creating a role.") from e

async def get_role_by_id(conn: Connection, role_id: UUID) -> Optional[Dict[str, Any]]:
    """Retrieves a role record from the database by its ID."""
    return await conn.fetchrow("SELECT id, short_name, long_name FROM role WHERE id = $1", role_id)

async def get_role_by_lookup(conn: Connection, short_name: Optional[str] = None, long_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a role record by its short or long name."""
    if short_name:
        return await conn.fetchrow("SELECT * FROM role WHERE short_name = $1", short_name)
    if long_name:
        return await conn.fetchrow("SELECT * FROM role WHERE long_name = $1", long_name)
    return None

async def list_roles(conn: Connection) -> List[Dict[str, Any]]:
    """Retrieves all role records from the database."""
    return await conn.fetch("SELECT id, short_name, long_name FROM role ORDER BY short_name;")

async def update_role(conn: Connection, role_id: UUID, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Updates an existing role record in the database."""
    fields, values = list(update_data.keys()), list(update_data.values())
    set_clause = ", ".join(f"{field} = ${i+1}" for i, field in enumerate(fields))
    query = f"UPDATE role SET {set_clause} WHERE id = ${len(fields) + 1} RETURNING id, short_name, long_name;"
    
    try:
        return await conn.fetchrow(query, *values, role_id)
    except UniqueViolationError as e:
        logger.error("db.role.update.failed_unique", error=str(e))
        raise ValueError("A role with the same short_name or long_name already exists.") from e

async def delete_role(conn: Connection, role_id: UUID) -> bool:
    """Deletes a role record from the database by its ID."""
    result = await conn.execute("DELETE FROM role WHERE id = $1", role_id)
    return result.strip() == "DELETE 1"

async def list_all_privileges(conn: Connection) -> List[str]:
    """Retrieves a flat list of all privileges from the privilege table."""
    query = "SELECT privilege FROM privilege ORDER BY privilege;"
    records = await conn.fetch(query)
    return [record['privilege'] for record in records]

async def get_role_short_name_by_id(conn: Connection, role_id: UUID) -> Optional[str]:
    """
    Fetches the short_name of a role by its ID.
    This is used to validate role assignments during application approval.
    """
    return await conn.fetchval("SELECT short_name FROM role WHERE id = $1", role_id)