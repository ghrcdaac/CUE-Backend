# ==============================================================================
# File: src/python/api/v2/utils/user_application.py (Corrected)
# --- MODIFIED to pass the request object on cross-utility calls ---
# ==============================================================================
from uuid import UUID
from typing import List, Dict, Any, Optional
import structlog
from fastapi import Request

# No longer need get_db_connection
# from core.db import get_db_connection
from v2.database_util import user_application as app_db
from v2.database_util import cueuser as user_db
from v2.database_util import role as role_db
from v2.database_util import ngroup as ngroup_db
from v2.type_util.auth import AuthUser as User
from v2.type_util.user_application import UserApplicationCreate, ApplicationStatus, AccountType
from v2.utils.cueuser import get_user_profile
from asyncpg.exceptions import UniqueViolationError, ForeignKeyViolationError
# --- Import the new event publisher utility ---
from .event_publisher import publish_event

logger = structlog.get_logger(__name__)

# The UUID for the special 'ESDIS Security' ngroup from your seed data
ESDIS_SECURITY_NGROUP_ID = UUID('0259fb55-1146-4461-ade2-57504e0c3ace')

class ApplicationNotFoundError(Exception):
    pass

class ApplicationInvalidStateError(Exception):
    pass

async def submit_application(request: Request, app_data: UserApplicationCreate, user_id: UUID) -> Dict[str, Any]:
    """Submits a new user application and publishes an event."""
    async with request.state.pool.acquire() as conn:
        new_app = await app_db.create_user_application(conn, app_data, user_id)
    
    # --- Publish event to notify admins ---
    publish_event(
        source="com.cue.api",
        detail_type="UserApplicationSubmitted",
        detail={"application_id": str(new_app['id'])}
    )
    
    logger.info("application.submitted", application_id=str(new_app['id']))
    return new_app

async def get_application(request: Request, application_id: UUID) -> Dict[str, Any]:
    """Retrieves a single application."""
    async with request.state.pool.acquire() as conn:
        app = await app_db.get_user_application_by_id(conn, application_id)
    if not app:
        raise ApplicationNotFoundError("Application not found.")
    return app

async def list_applications(
    request: Request,
    user: User, # Accept the full user object for role checks
    active_ngroup_id: Optional[str] = None, # Accept the optional ngroup ID string
    status: Optional[ApplicationStatus] = None,
    is_spam: Optional[bool] = None
) -> List[Dict[str, Any]]:
    """Lists all applications based on user roles and optional filters."""

    # Convert string UUID from header to UUID object, or None
    ngroup_id_to_filter = UUID(active_ngroup_id) if active_ngroup_id else None

    async with request.state.pool.acquire() as conn:
        # Call the new, more powerful list_user_applications function
        return await app_db.list_user_applications(
            conn,
            requesting_user=user.model_dump(),
            active_ngroup_id=ngroup_id_to_filter,
            status=status,
            is_spam=is_spam
        )

async def approve_application(request: Request, application_id: UUID, role_id_to_assign: UUID, approver: User, provider_id_to_assign: Optional[UUID] = None) -> Dict[str, Any]:
    """
    Approves an application, creates the user in the local CUE database,
    and publishes an approval event.
    """
    logger.info("application.approval.started", application_id=str(application_id), approver_id=str(approver.id))
    try:
        async with request.state.pool.acquire() as conn:
            role_to_assign = await role_db.get_role_short_name_by_id(conn, role_id_to_assign)
            if not role_to_assign:
                raise ValueError("The specified role does not exist.")

            approver_roles = set(approver.roles)
            if "admin" not in approver_roles:
                if "daac_manager" in approver_roles:
                    allowed_roles = {"daac_manager", "daac_staff", "daac_observer", "provider"}
                    if role_to_assign not in allowed_roles:
                        raise ValueError(f"DAAC Managers may only assign roles: {', '.join(allowed_roles)}.")
                elif "security" in approver_roles:
                    if role_to_assign != "security":
                        raise ValueError("Security users may only assign the 'security' role.")
                else:
                    raise ValueError("You do not have permission to assign roles.")

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
                
                if app_data['ngroup_id'] == ESDIS_SECURITY_NGROUP_ID:
                    all_ngroup_ids = await ngroup_db.list_all_ngroup_ids(conn)
                    await user_db.assign_ngroups_to_user(conn, user_id, all_ngroup_ids)
                    logger.info("user.creation.security", user_id=str(user_id), assigned_all_ngroups=len(all_ngroup_ids))
                else:
                    ngroups_to_assign = [app_data['ngroup_id']]
                    final_provider_id = provider_id_to_assign if provider_id_to_assign is not None else app_data.get('provider_id')
                    providers_to_assign = [final_provider_id] if final_provider_id else []
                    
                    await user_db.assign_ngroups_to_user(conn, user_id, ngroups_to_assign)
                    if providers_to_assign:
                        await user_db.assign_providers_to_user(conn, user_id, providers_to_assign)
                    
                    if provider_id_to_assign is not None and provider_id_to_assign != app_data.get('provider_id'):
                        await conn.execute("UPDATE user_application SET provider_id = $1 WHERE id = $2", provider_id_to_assign, application_id)
                
                await app_db.update_application_status(conn, application_id, ApplicationStatus.APPROVED)

        # --- Pass the request object to the user utility function ---
        new_user_profile = await get_user_profile(request, user_id)

        # --- Publish event to notify the user of their approval ---
        publish_event(
            source="com.cue.api",
            detail_type="UserApplicationApproved",
            detail={"user_id": str(user_id)}
        )

        logger.info("application.approval.completed", application_id=str(application_id), new_user_id=str(user_id))
        return new_user_profile
            
    except (UniqueViolationError, ForeignKeyViolationError) as e:
        logger.error("application.approval.db_error", application_id=str(application_id), error=str(e))
        raise ValueError("Failed to approve application. The user may already exist, or an invalid role/group was provided.")
    except Exception as e:
        logger.error("application.approval.failed", application_id=str(application_id), exc_info=True)
        raise e

async def reject_application(request: Request, application_id: UUID, mark_as_spam: bool = False) -> Dict[str, Any]:
    """Rejects a pending user application, optionally blocking future requests from the email."""
    logger.info("application.rejection.started", application_id=str(application_id), mark_as_spam=mark_as_spam)
    async with request.state.pool.acquire() as conn:
        app_data = await app_db.get_user_application_by_id(conn, application_id)
        if not app_data:
            raise ApplicationNotFoundError("Application not found.")
        if app_data['status'] != 'pending':
            raise ApplicationInvalidStateError(f"Application is not in 'pending' state. Current status: {app_data['status']}")

        if mark_as_spam:
            async with conn.transaction():
                updated_apps = await app_db.mark_email_as_spam(conn, app_data['email'])
            updated_app = next((app for app in updated_apps if app['id'] == application_id), None)
        else:
            await app_db.delete_user_application(conn, application_id)
            updated_app = {**app_data, 'status': ApplicationStatus.REJECTED, 'is_spam': False}

    logger.info("application.rejection.completed", application_id=str(application_id), marked_as_spam=mark_as_spam)
    return updated_app

async def unmark_spam_application(request: Request, application_id: UUID) -> Dict[str, Any]:
    """Unmarks a user application as spam, keeping the status as rejected and setting is_spam to False."""
    logger.info("application.unmark_spam.started", application_id=str(application_id))
    async with request.state.pool.acquire() as conn:
        app_data = await app_db.get_user_application_by_id(conn, application_id)
        if not app_data:
            raise ApplicationNotFoundError("Application not found.")
        
        await app_db.delete_user_application(conn, application_id)
        updated_app = {**app_data, 'status': ApplicationStatus.REJECTED, 'is_spam': False}

    logger.info("application.unmark_spam.completed", application_id=str(application_id))
    return updated_app
