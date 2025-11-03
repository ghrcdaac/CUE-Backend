# ==============================================================================
# File: src/python/api/v2/database_util/cueuser.py
# Purpose: Contains all raw SQL queries for user management.
# ==============================================================================
from asyncpg import Connection, ForeignKeyViolationError
from typing import List, Dict, Any, Optional
from uuid import UUID
import structlog
import json

logger = structlog.get_logger(__name__)

# --- User Read Queries ---

async def get_user_by_id(conn: Connection, user_id: UUID) -> Optional[Dict[str, Any]]:
    """
    
    Fetches a user's complete profile using efficient subqueries instead of multiple JOINs
    to prevent row duplication before aggregation.
    """
    query = """
        SELECT
            u.id, u.email, u.name, u.cueusername, u.edpub_id, u.registered,
            (
                SELECT COALESCE(jsonb_agg(r.short_name), '[]'::jsonb)
                FROM cueuser_role ur
                JOIN role r ON ur.role_id = r.id
                WHERE ur.cueuser_id = u.id
            ) AS roles,
            (
                SELECT COALESCE(jsonb_agg(jsonb_build_object('id', g.id, 'short_name', g.short_name)), '[]'::jsonb)
                FROM cueuser_ngroup ug
                JOIN ngroup g ON ug.ngroup_id = g.id
                WHERE ug.cueuser_id = u.id
            ) AS ngroups,
            (
                SELECT COALESCE(jsonb_agg(DISTINCT p.privilege), '[]'::jsonb)
                FROM cueuser_role ur
                JOIN role_privilege rp ON ur.role_id = rp.role_id
                JOIN privilege p ON rp.privilege_id = p.id
                WHERE ur.cueuser_id = u.id
            ) AS privileges
        FROM cueuser u
        WHERE u.id = $1;
    """
    return await conn.fetchrow(query, user_id)

async def list_users(
    conn: Connection,
    requesting_user: Dict[str, Any],
    active_ngroup_id: Optional[UUID] = None
) -> List[Dict[str, Any]]:
    """
    Fetches users, filtered by the active ngroup and user role.
    - Admins/Security see all users in the selected DAAC, or all users if none is selected.
    - Managers see only users within the selected DAAC.
    """
    logger.info(
        "user.list.executing_query",
        user_roles=requesting_user.get('roles', []),
        active_ngroup_id=str(active_ngroup_id) if active_ngroup_id else None
    )
    
    user_roles = set(requesting_user.get('roles', []))
    params = []
    
    # Base query uses efficient subqueries to aggregate related data
    base_query = """
        SELECT
            u.id, u.email, u.name, u.cueusername, u.edpub_id, u.registered,
            (
                SELECT COALESCE(jsonb_agg(r.short_name), '[]'::jsonb)
                FROM cueuser_role ur JOIN role r ON ur.role_id = r.id
                WHERE ur.cueuser_id = u.id
            ) AS roles,
            (
                SELECT COALESCE(jsonb_agg(jsonb_build_object('id', g.id, 'short_name', g.short_name)), '[]'::jsonb)
                FROM cueuser_ngroup ug JOIN ngroup g ON ug.ngroup_id = g.id
                WHERE ug.cueuser_id = u.id
            ) AS ngroups,
            (
                SELECT COALESCE(jsonb_agg(DISTINCT p.privilege), '[]'::jsonb)
                FROM cueuser_role ur
                JOIN role_privilege rp ON ur.role_id = rp.role_id
                JOIN privilege p ON rp.privilege_id = p.id
                WHERE ur.cueuser_id = u.id
            ) AS privileges
        FROM cueuser u
    """
    
    # Use an EXISTS subquery for efficient filtering without disturbing the main query structure
    where_conditions = []
    if active_ngroup_id:
        where_conditions.append(
            "EXISTS (SELECT 1 FROM cueuser_ngroup ug WHERE ug.cueuser_id = u.id AND ug.ngroup_id = $1)"
        )
        params.append(active_ngroup_id)
    else:
        # If no DAAC is selected:
        # Admins/Security can see all users across all DAACs.
        if 'admin' not in user_roles and 'security' not in user_roles:
            # All other roles (e.g., managers) MUST select a DAAC to see any users.
            # This is a secure default to prevent accidental data exposure.
            where_conditions.append("FALSE")

    where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
    query = f"{base_query} {where_clause} ORDER BY u.name;"
    
    return await conn.fetch(query, *params)

async def get_user_by_username(conn: Connection, cueusername: str) -> Optional[Dict[str, Any]]:
    """Fetches a single user's core data by their unique username."""
    # This query is simple enough that it doesn't need the subquery optimization.
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
        conditions.append(f"u.email ILIKE ${len(params)}")
    if cueusername:
        params.append(f"%{cueusername}%")
        conditions.append(f"u.cueusername ILIKE ${len(params)}")
    if name:
        params.append(f"%{name}%")
        conditions.append(f"u.name ILIKE ${len(params)}")
    if edpub_id:
        params.append(edpub_id)
        conditions.append(f"u.edpub_id = ${len(params)}")

    if not conditions:
        return []

    # --- Corrected parameter indexing logic ---
    where_clause = " OR ".join(conditions)
    query = f"""
        SELECT
            u.id, u.email, u.name, u.cueusername, u.edpub_id, u.registered,
            (
                SELECT COALESCE(jsonb_agg(g.short_name), '[]'::jsonb)
                FROM cueuser_ngroup ug JOIN ngroup g ON ug.ngroup_id = g.id
                WHERE ug.cueuser_id = u.id
            ) AS ngroups
        FROM cueuser u
        WHERE {where_clause}
        GROUP BY u.id;
    """
    return await conn.fetch(query, *params)

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
    
    Fetches auth details using the same efficient subquery pattern.
    """
    query = """
        SELECT
            (
                SELECT COALESCE(jsonb_agg(r.short_name), '[]'::jsonb)
                FROM cueuser_role ur JOIN role r ON ur.role_id = r.id
                WHERE ur.cueuser_id = u.id
            ) AS roles,
            (
                SELECT COALESCE(jsonb_agg(jsonb_build_object('id', g.id, 'short_name', g.short_name)), '[]'::jsonb)
                FROM cueuser_ngroup ug JOIN ngroup g ON ug.ngroup_id = g.id
                WHERE ug.cueuser_id = u.id
            ) AS ngroups,
            (
                SELECT COALESCE(jsonb_agg(DISTINCT p.privilege), '[]'::jsonb)
                FROM cueuser_role ur
                JOIN role_privilege rp ON ur.role_id = rp.role_id
                JOIN privilege p ON rp.privilege_id = p.id
                WHERE ur.cueuser_id = u.id
            ) AS privileges
        FROM cueuser u
        WHERE u.id = $1;
    """
    return await conn.fetchrow(query, user_id)

# --- User & Association Write Queries ---

async def create_user(conn: Connection, user_id: UUID, email: str, name: str, cueusername: str, edpub_id: Optional[str]) -> Dict[str, Any]:
    """--- OPTIMIZED: Creates a new user and returns the created record. ---"""
    return await conn.fetchrow(
        "INSERT INTO cueuser (id, email, name, cueusername, edpub_id) VALUES ($1, $2, $3, $4, $5) RETURNING *;",
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

async def update_user(conn: Connection, user_id: UUID, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """--- OPTIMIZED: Updates user details and returns the full updated record. ---"""
    fields, values = list(update_data.keys()), list(update_data.values())
    set_clause = ", ".join(f"{field} = ${i+1}" for i, field in enumerate(fields))
    query = f"UPDATE cueuser SET {set_clause} WHERE id = ${len(fields) + 1} RETURNING *;"
    return await conn.fetchrow(query, *values, user_id)

async def update_user_roles(conn: Connection, user_id: UUID, role_ids: List[UUID]):
    """Replaces a user's existing roles with a new list of roles."""
    async with conn.transaction():
        await conn.execute("DELETE FROM cueuser_role WHERE cueuser_id = $1", user_id)
        if role_ids:
            await conn.executemany("INSERT INTO cueuser_role (cueuser_id, role_id) VALUES ($1, $2)",
                                   [(user_id, role_id) for role_id in role_ids])

async def remove_all_user_associations(conn: Connection, user_id: UUID):
    """Deletes all associations for a user."""
    async with conn.transaction():
        await conn.execute("DELETE FROM cueuser_role WHERE cueuser_id = $1", user_id)
        await conn.execute("DELETE FROM cueuser_ngroup WHERE cueuser_id = $1", user_id)
        await conn.execute("DELETE FROM cueuser_provider WHERE cueuser_id = $1", user_id)

async def delete_user(conn: Connection, user_id: UUID) -> bool:
    """Deletes a user from the cueuser table."""
    result = await conn.execute("DELETE FROM cueuser WHERE id = $1", user_id)
    deleted_count = int(result.split(" ")[1])
    return deleted_count > 0