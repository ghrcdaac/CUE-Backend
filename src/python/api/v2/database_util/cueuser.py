# ==============================================================================
# File: src/python/api/v2/database_util/cueuser.py (Final)
# Purpose: Contains all raw SQL queries for user management.
# ==============================================================================
from asyncpg import Connection
from typing import List, Dict, Any, Optional
from uuid import UUID
import structlog
import json

logger = structlog.get_logger(__name__)

# --- User Read Queries ---

async def get_user_by_id(conn: Connection, user_id: UUID) -> Optional[Dict[str, Any]]:
    """Fetches a single user's core data and their associated roles and ngroups."""
    query = """
        SELECT
            u.id, u.email, u.name, u.cueusername, u.edpub_id, u.registered,
            COALESCE(jsonb_agg(DISTINCT r.short_name) FILTER (WHERE r.short_name IS NOT NULL), '[]'::jsonb) AS roles,
            COALESCE(jsonb_agg(DISTINCT g.short_name) FILTER (WHERE g.short_name IS NOT NULL), '[]'::jsonb) AS ngroups
        FROM cueuser u
        LEFT JOIN cueuser_role ur ON u.id = ur.cueuser_id
        LEFT JOIN role r ON ur.role_id = r.id
        LEFT JOIN cueuser_ngroup ug ON u.id = ug.cueuser_id
        LEFT JOIN ngroup g ON ug.ngroup_id = g.id
        WHERE u.id = $1
        GROUP BY u.id;
    """
    return await conn.fetchrow(query, user_id)

async def get_user_by_username(conn: Connection, cueusername: str) -> Optional[Dict[str, Any]]:
    """Fetches a single user's core data by their unique username."""
    query = """
        SELECT
            u.id, u.email, u.name, u.cueusername, u.edpub_id, u.registered,
            COALESCE(jsonb_agg(DISTINCT r.short_name) FILTER (WHERE r.short_name IS NOT NULL), '[]'::jsonb) AS roles,
            COALESCE(jsonb_agg(DISTINCT g.short_name) FILTER (WHERE g.short_name IS NOT NULL), '[]'::jsonb) AS ngroups
        FROM cueuser u
        LEFT JOIN cueuser_role ur ON u.id = ur.cueuser_id
        LEFT JOIN role r ON ur.role_id = r.id
        LEFT JOIN cueuser_ngroup ug ON u.id = ug.cueuser_id
        LEFT JOIN ngroup g ON ug.ngroup_id = g.id
        WHERE u.cueusername = $1
        GROUP BY u.id;
    """
    return await conn.fetchrow(query, cueusername)

async def find_user(conn: Connection, email: Optional[str], cueusername: Optional[str], name: Optional[str], edpub_id: Optional[str]) -> List[Dict[str, Any]]:
    """Finds users based on a variety of optional criteria."""
    conditions = []
    params = []
    
    if email:
        params.append(f"%{email}%")
        conditions.append(f"u.email ILIKE ${len(params) + 1}")
    if cueusername:
        params.append(f"%{cueusername}%")
        conditions.append(f"u.cueusername ILIKE ${len(params) + 1}")
    if name:
        params.append(f"%{name}%")
        conditions.append(f"u.name ILIKE ${len(params) + 1}")
    if edpub_id:
        params.append(edpub_id)
        conditions.append(f"u.edpub_id = ${len(params) + 1}")

    if not conditions:
        return []

    where_clause = " OR ".join(conditions)
    query = f"""
        SELECT
            u.id, u.email, u.name, u.cueusername, u.edpub_id, u.registered,
            COALESCE(jsonb_agg(DISTINCT g.short_name) FILTER (WHERE g.short_name IS NOT NULL), '[]'::jsonb) AS ngroups
        FROM cueuser u
        LEFT JOIN cueuser_ngroup ug ON u.id = ug.cueuser_id
        LEFT JOIN ngroup g ON ug.ngroup_id = g.id
        WHERE {where_clause}
        GROUP BY u.id;
    """
    return await conn.fetch(query, *params)


async def list_users_by_ngroup(conn: Connection, ngroup_id: UUID) -> List[Dict[str, Any]]:
    """Lists all users associated with a specific ngroup, including their roles."""
    query = """
        SELECT
            u.id, u.email, u.name, u.cueusername, u.edpub_id, u.registered,
            COALESCE(jsonb_agg(DISTINCT r.short_name) FILTER (WHERE r.short_name IS NOT NULL), '[]'::jsonb) AS roles
        FROM cueuser u
        INNER JOIN cueuser_ngroup ug ON u.id = ug.cueuser_id
        LEFT JOIN cueuser_role ur ON u.id = ur.cueuser_id
        LEFT JOIN role r ON ur.role_id = r.id
        WHERE ug.ngroup_id = $1
        GROUP BY u.id;
    """
    return await conn.fetch(query, ngroup_id)

async def list_users_by_role(conn: Connection, role_id: UUID) -> List[Dict[str, Any]]:
    """Lists all users assigned a specific role."""
    query = """
        SELECT u.id, u.email, u.name, u.cueusername, u.edpub_id, u.registered
        FROM cueuser u
        INNER JOIN cueuser_role ur ON u.id = ur.cueuser_id
        WHERE ur.role_id = $1;
    """
    return await conn.fetch(query, role_id)

async def user_exists_by_id(conn: Connection, user_id: UUID) -> bool:
    """Checks if a user exists in the cueuser table by their ID."""
    query = "SELECT EXISTS(SELECT 1 FROM cueuser WHERE id = $1);"
    return await conn.fetchval(query, user_id)

async def get_user_auth_details(conn: Connection, user_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Fetches roles, ngroups (as objects with id and name), and all associated 
    privileges for an authenticated user.
    """
    query = """
        SELECT
            COALESCE(jsonb_agg(DISTINCT r.short_name) FILTER (WHERE r.short_name IS NOT NULL), '[]'::jsonb) AS roles,
            COALESCE(jsonb_agg(DISTINCT jsonb_build_object('id', g.id, 'short_name', g.short_name)) FILTER (WHERE g.id IS NOT NULL), '[]'::jsonb) AS ngroups,
            COALESCE(jsonb_agg(DISTINCT p.privilege) FILTER (WHERE p.privilege IS NOT NULL), '[]'::jsonb) AS privileges
        FROM cueuser u
        LEFT JOIN cueuser_role ur ON u.id = ur.cueuser_id
        LEFT JOIN role r ON ur.role_id = r.id
        LEFT JOIN role_privilege rp ON r.id = rp.role_id
        LEFT JOIN privilege p ON rp.privilege = p.privilege
        LEFT JOIN cueuser_ngroup ug ON u.id = ug.cueuser_id
        LEFT JOIN ngroup g ON ug.ngroup_id = g.id
        WHERE u.id = $1
        GROUP BY u.id;
    """
    return await conn.fetchrow(query, user_id)

# --- User & Association Write Queries ---

async def create_user(conn: Connection, user_id: UUID, email: str, name: str, cueusername: str, edpub_id: Optional[str]):
    """Creates a new user record in the cueuser table."""
    await conn.execute(
        "INSERT INTO cueuser (id, email, name, cueusername, edpub_id) VALUES ($1, $2, $3, $4, $5)",
        user_id, email, name, cueusername, edpub_id
    )

async def assign_role_to_user(conn: Connection, user_id: UUID, role_id: UUID):
    """Assigns a single role to a user."""
    await conn.execute("INSERT INTO cueuser_role (cueuser_id, role_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", user_id, role_id)

async def assign_ngroups_to_user(conn: Connection, user_id: UUID, ngroup_ids: List[UUID]):
    """Assigns a list of ngroups to a user."""
    await conn.executemany("INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                           [(user_id, ngroup_id) for ngroup_id in ngroup_ids])

async def assign_providers_to_user(conn: Connection, user_id: UUID, provider_ids: List[UUID]):
    """Assigns a list of providers to a user."""
    await conn.executemany("INSERT INTO cueuser_provider (cueuser_id, provider_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                           [(user_id, provider_id) for provider_id in provider_ids])

async def update_user(conn: Connection, user_id: UUID, update_data: Dict[str, Any]):
    """Updates a user's core details in the cueuser table."""
    fields, values = list(update_data.keys()), list(update_data.values())
    set_clause = ", ".join(f"{field} = ${i+1}" for i, field in enumerate(fields))
    query = f"UPDATE cueuser SET {set_clause} WHERE id = ${len(fields) + 1} RETURNING id;"
    await conn.execute(query, *values, user_id)

async def update_user_roles(conn: Connection, user_id: UUID, role_ids: List[UUID]):
    """Replaces a user's existing roles with a new list of roles."""
    await conn.execute("DELETE FROM cueuser_role WHERE cueuser_id = $1", user_id)
    if role_ids:
        await conn.executemany("INSERT INTO cueuser_role (cueuser_id, role_id) VALUES ($1, $2)",
                               [(user_id, role_id) for role_id in role_ids])

async def update_user_ngroups(conn: Connection, user_id: UUID, ngroup_ids: List[UUID]):
    """Replaces a user's existing ngroup associations with a new list."""
    await conn.execute("DELETE FROM cueuser_ngroup WHERE cueuser_id = $1", user_id)
    if ngroup_ids:
        await assign_ngroups_to_user(conn, user_id, ngroup_ids)

# --- User & Association Deletion Queries ---

async def remove_all_user_associations(conn: Connection, user_id: UUID):
    """Explicitly deletes all associations for a user for a clean delete."""
    logger.info("db.associations.delete", user_id=str(user_id))
    await conn.execute("DELETE FROM cueuser_role WHERE cueuser_id = $1", user_id)
    await conn.execute("DELETE FROM cueuser_ngroup WHERE cueuser_id = $1", user_id)
    await conn.execute("DELETE FROM cueuser_provider WHERE cueuser_id = $1", user_id)

async def delete_user(conn: Connection, user_id: UUID) -> bool:
    """
    Deletes a user from the cueuser table.
    """
    result = await conn.execute("DELETE FROM cueuser WHERE id = $1", user_id)
    return result.strip() == "DELETE 1"


async def get_user_by_id(conn: Connection, user_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Fetches a single user's core data, including their associated roles,
    ngroups (as objects), and a consolidated list of all their privileges.
    """
    # --- Updated jsonb_agg for ngroups to build objects ---
    query = """
        SELECT
            u.id, u.email, u.name, u.cueusername, u.edpub_id, u.registered,
            COALESCE(jsonb_agg(DISTINCT r.short_name) FILTER (WHERE r.short_name IS NOT NULL), '[]'::jsonb) AS roles,
            COALESCE(jsonb_agg(DISTINCT jsonb_build_object('id', g.id, 'short_name', g.short_name)) FILTER (WHERE g.id IS NOT NULL), '[]'::jsonb) AS ngroups,
            COALESCE(jsonb_agg(DISTINCT p.privilege) FILTER (WHERE p.privilege IS NOT NULL), '[]'::jsonb) AS privileges
        FROM cueuser u
        LEFT JOIN cueuser_role ur ON u.id = ur.cueuser_id
        LEFT JOIN role r ON ur.role_id = r.id
        LEFT JOIN role_privilege rp ON r.id = rp.role_id
        LEFT JOIN privilege p ON rp.privilege = p.privilege
        LEFT JOIN cueuser_ngroup ug ON u.id = ug.cueuser_id
        LEFT JOIN ngroup g ON ug.ngroup_id = g.id
        WHERE u.id = $1
        GROUP BY u.id;
    """
    return await conn.fetchrow(query, user_id)

async def list_users(conn: Connection) -> List[Dict[str, Any]]:
    """
    Fetches a list of all users with their associated roles and ngroups.
    """
    query = """
        SELECT
            u.id, u.email, u.name, u.cueusername, u.edpub_id, u.registered,
            COALESCE(jsonb_agg(DISTINCT r.short_name) FILTER (WHERE r.short_name IS NOT NULL), '[]'::jsonb) AS roles,
            COALESCE(jsonb_agg(DISTINCT g.short_name) FILTER (WHERE g.short_name IS NOT NULL), '[]'::jsonb) AS ngroups
        FROM cueuser u
        LEFT JOIN cueuser_role ur ON u.id = ur.cueuser_id
        LEFT JOIN role r ON ur.role_id = r.id
        LEFT JOIN cueuser_ngroup ug ON u.id = ug.cueuser_id
        LEFT JOIN ngroup g ON ug.ngroup_id = g.id
        GROUP BY u.id
        ORDER BY u.name;
    """
    return await conn.fetch(query)