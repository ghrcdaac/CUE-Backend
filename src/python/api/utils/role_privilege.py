from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import role_privilege as role_privilege_db
from lambda_utils.type_util.role_privilege import RolePrivilegeCreate, RolePrivilegeReturn
from typing import List
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class RolePrivilegeAssociationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)

class RolePrivilegeNotFoundError(Exception):
    def __init__(self, role_id: UUID, privilege: str):
        super().__init__(f"Association between Role ID: {role_id} and Privilege: {privilege} not found")
        self.role_id = role_id
        self.privilege = privilege

async def create_role_privilege_association(data: RolePrivilegeCreate) -> bool:
    """Associates a role with a privilege."""
    pool: Pool = await get_connection_pool()
    params = (data.role_id, data.privilege)
    try:
        result = await query(pool, role_privilege_db.create_role_privilege_association_in_db, params)
        return result
    except ValueError as e:
        logger.error(f"Error associating role with privilege: {e}", exc_info=True)
        raise RolePrivilegeAssociationError(str(e))
    finally:
        await pool.close()

async def delete_role_privilege_association(data: RolePrivilegeCreate) -> bool:
    """Removes the association between a role and a privilege."""
    pool: Pool = await get_connection_pool()
    params = (data.role_id, data.privilege)
    try:
        result = await query(pool, role_privilege_db.delete_role_privilege_association_from_db, params)
        if not result:
            raise RolePrivilegeNotFoundError(data.role_id, data.privilege)
        return result
    except Exception as e:
        logger.error(f"Error removing association between role and privilege: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_privileges_for_role(role_name: str) -> List[str]: # changed role_id: UUID to role_name: str
    """Retrieves all privileges associated with a role."""
    pool: Pool = await get_connection_pool()
    params = (role_name,) # Changed
    try:
        # Note:  We don't need a custom Pydantic model for the return *here*
        # because we're just returning a list of strings (privilege names).
        privileges = await query(pool, role_privilege_db.list_privileges_for_role_from_db, params)
        # The database function returns a list of records.  We need to extract
        # the 'privilege' value from each record.  This uses a list comprehension.
        return [p['privilege'] for p in privileges] # Extract 'privilege', not 'role_id'
    except Exception as e:
        logger.error(f"Error listing privileges for role: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_roles_with_privilege(privilege: str) -> List[UUID]:
    """Retrieves all role IDs associated with a privilege."""
    pool: Pool = await get_connection_pool()
    params = (privilege,)
    try:
        return await query(pool, role_privilege_db.list_roles_with_privilege_from_db, params)
    except Exception as e:
        logger.error(f"Error listing roles with privilege: {e}", exc_info=True)
        raise
    finally:
        await pool.close()