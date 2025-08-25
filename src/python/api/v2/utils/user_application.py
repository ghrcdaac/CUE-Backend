# File: src/python/api/v2/utils/user_application.py (Updated)

from uuid import UUID
from typing import List, Dict, Any, Optional
import structlog

from core.db import get_db_connection
from v2.database_util import user_application as app_db
from v2.database_util import cueuser as user_db
# --- ADDED: New dependencies for validation and security user creation ---
from v2.database_util import role as role_db
from v2.database_util import ngroup as ngroup_db
from v2.type_util.auth import AuthUser as User
from v2.type_util.user_application import UserApplicationCreate, ApplicationStatus, AccountType
from v2.utils.cueuser import get_user_profile
from asyncpg.exceptions import UniqueViolationError, ForeignKeyViolationError

logger = structlog.get_logger(__name__)

# The UUID for the special 'ESDIS Security' ngroup from your seed data. Refer and change the Seed.sql values is this UUID changes.
ESDIS_SECURITY_NGROUP_ID = UUID('0259fb55-1146-4461-ade2-57504e0c3ace')

class ApplicationNotFoundError(Exception):
    pass

class ApplicationInvalidStateError(Exception):
    pass

async def submit_application(app_data: UserApplicationCreate, user_id: UUID) -> Dict[str, Any]:
    """Submits a new user application."""
    async with get_db_connection() as conn:
        new_app = await app_db.create_user_application(conn, app_data, user_id)
    
    logger.info("application.submitted", application_id=str(new_app['id']))
    return new_app

async def get_application(application_id: UUID) -> Dict[str, Any]:
    """Retrieves a single application."""
    async with get_db_connection() as conn:
        app = await app_db.get_user_application_by_id(conn, application_id)
    if not app:
        raise ApplicationNotFoundError("Application not found.")
    return app

async def list_applications(ngroup_id: Optional[UUID] = None, status: Optional[ApplicationStatus] = None) -> List[Dict[str, Any]]:
    """Lists all applications based on optional filters."""
    async with get_db_connection() as conn:
        return await app_db.list_user_applications(conn, ngroup_id, status)

async def approve_application(application_id: UUID, role_id_to_assign: UUID, approver: User) -> Dict[str, Any]:
    """
    Approves an application, creates the user in the local CUE database,
    and enforces role assignment permissions.
    """
    logger.info("application.approval.started", application_id=str(application_id), approver_id=str(approver.id))
    try:
        async with get_db_connection() as conn:
            # --- START: New validation logic ---
            role_to_assign = await role_db.get_role_short_name_by_id(conn, role_id_to_assign)
            if not role_to_assign:
                raise ValueError("The specified role does not exist.")

            approver_roles = set(approver.roles)
            if "admin" not in approver_roles:
                if "daac_manager" in approver_roles:
                    allowed_roles = {"daac_staff", "daac_observer", "provider"}
                    if role_to_assign not in allowed_roles:
                        raise ValueError(f"DAAC Managers may only assign roles: {', '.join(allowed_roles)}.")
                elif "security" in approver_roles:
                    if role_to_assign != "security":
                        raise ValueError("Security users may only assign the 'security' role.")
                else:
                    raise ValueError("You do not have permission to assign roles.")
            # --- END: New validation logic ---

            app_data = await app_db.get_user_application_by_id(conn, application_id)
            if not app_data:
                raise ApplicationNotFoundError("Application not found.")
            if app_data['status'] != 'pending':
                raise ApplicationInvalidStateError(f"Application is not in 'pending' state.")

            user_id = app_data['user_id']
            if not user_id:
                raise ValueError("Application is missing the required user_id from Keycloak.")

            async with conn.transaction():
                await user_db.create_user(
                    conn, user_id, app_data['email'], app_data['name'], 
                    app_data['username'], app_data['edpub_id']
                )
                await user_db.assign_role_to_user(conn, user_id, role_id_to_assign)
                
                # --- START: Special handling for Security user creation ---
                if app_data['ngroup_id'] == ESDIS_SECURITY_NGROUP_ID:
                    all_ngroup_ids = await ngroup_db.list_all_ngroup_ids(conn)
                    await user_db.assign_ngroups_to_user(conn, user_id, all_ngroup_ids)
                    logger.info("user.creation.security", user_id=str(user_id), assigned_all_ngroups=len(all_ngroup_ids))
                # --- END: Special handling ---
                else:
                    # Standard user creation logic
                    ngroups_to_assign = [app_data['ngroup_id']]
                    providers_to_assign = [app_data['provider_id']] if app_data.get('provider_id') else []
                    
                    await user_db.assign_ngroups_to_user(conn, user_id, ngroups_to_assign)
                    if providers_to_assign:
                        await user_db.assign_providers_to_user(conn, user_id, providers_to_assign)
                
                await app_db.update_application_status(conn, application_id, ApplicationStatus.APPROVED)

        new_user_profile = await get_user_profile(user_id)
        
        logger.info("application.approval.completed", application_id=str(application_id), new_user_id=str(user_id))
        return new_user_profile
            
    except (UniqueViolationError, ForeignKeyViolationError) as e:
        logger.error("application.approval.db_error", application_id=str(application_id), error=str(e))
        raise ValueError("Failed to approve application. The user may already exist, or an invalid role/group was provided.")
    except Exception as e:
        logger.error("application.approval.failed", application_id=str(application_id), exc_info=True)
        raise e

async def reject_application(application_id: UUID) -> Dict[str, Any]:
    """Rejects a pending user application."""
    logger.info("application.rejection.started", application_id=str(application_id))
    async with get_db_connection() as conn:
        app_data = await app_db.get_user_application_by_id(conn, application_id)
        if not app_data:
            raise ApplicationNotFoundError("Application not found.")
        if app_data['status'] != 'pending':
            raise ApplicationInvalidStateError(f"Application is not in 'pending' state. Current status: {app_data['status']}")
            
        updated_app = await app_db.update_application_status(conn, application_id, ApplicationStatus.REJECTED)
    logger.info("application.rejection.completed", application_id=str(application_id))
    return updated_app