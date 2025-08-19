# ==============================================================================
# File: src/python/api/v2/utils/user_application.py (Final)
# Purpose: Contains the business logic for the user application workflow.
# ==============================================================================
from uuid import UUID
from typing import List, Dict, Any, Optional
import structlog

from core.db import get_db_connection
from v2.database_util import user_application as app_db
from v2.database_util import cueuser as user_db # Needed for direct DB operations
from v2.type_util.user_application import UserApplicationCreate, ApplicationStatus, AccountType
from v2.utils.cueuser import get_user_profile # We still need this to return the full user

# from v2.utils.notification_publisher import publish_event

logger = structlog.get_logger(__name__)

class ApplicationNotFoundError(Exception):
    pass

class ApplicationInvalidStateError(Exception):
    pass

async def submit_application(app_data: UserApplicationCreate, user_id: UUID) -> Dict[str, Any]:
    """Submits a new user application and publishes an event."""
    async with get_db_connection() as conn:
        new_app = await app_db.create_user_application(conn, app_data, user_id)
    
    # await publish_event(
    #     source="com.cue.api",
    #     detail_type="UserApplicationSubmitted",
    #     detail={"application_id": str(new_app['id'])}
    # )
    
    logger.info("application.submitted", application_id=str(new_app['id']))
    return new_app

async def get_application(application_id: UUID) -> Dict[str, Any]:
    """Retrieves a single application."""
    async with get_db_connection() as conn:
        app = await app_db.get_user_application_by_id(conn, application_id)
    if not app:
        raise ApplicationNotFoundError()
    return app

async def list_applications(ngroup_id: Optional[UUID] = None, status: Optional[ApplicationStatus] = None) -> List[Dict[str, Any]]:
    """Lists all applications based on optional filters."""
    async with get_db_connection() as conn:
        return await app_db.list_user_applications(conn, ngroup_id, status)

async def approve_application(application_id: UUID, role_id: UUID) -> Dict[str, Any]:
    """
    Approves an application, creates the user in the local CUE database,
    and publishes an approval event.
    """
    logger.info("application.approval.started", application_id=str(application_id))
    async with get_db_connection() as conn:
        app_data = await app_db.get_user_application_by_id(conn, application_id)
        if not app_data:
            raise ApplicationNotFoundError()
        if app_data['status'] != 'pending':
            raise ApplicationInvalidStateError(f"Application is not in 'pending' state.")

        user_id = app_data['user_id']
        if not user_id:
            raise ValueError("Application is missing the required user_id from Keycloak.")

        # --- CHANGE: Perform user creation directly in the database ---
        async with conn.transaction():
            # 1. Create the user in the cueuser table
            await user_db.create_user(
                conn, user_id, app_data['email'], app_data['name'], 
                app_data['username'], app_data['edpub_id']
            )
            # 2. Assign the selected role
            await user_db.assign_role_to_user(conn, user_id, role_id)
            
            # 3. Assign ngroup and/or provider
            if app_data['account_type'] == AccountType.DAAC.value:
                await user_db.assign_ngroups_to_user(conn, user_id, [app_data['ngroup_id']])
            elif app_data['account_type'] == AccountType.PROVIDER.value:
                await user_db.assign_ngroups_to_user(conn, user_id, [app_data['ngroup_id']])
                await user_db.assign_providers_to_user(conn, user_id, [app_data['provider_id']])
            
            # 4. Update the application status
            await app_db.update_application_status(conn, application_id, ApplicationStatus.APPROVED)

    # Fetch the full profile of the newly created user to return to the frontend
    new_user_profile = await get_user_profile(user_id)

    # await publish_event(
    #     source="com.cue.api",
    #     detail_type="UserApplicationApproved",
    #     detail={"user_id": str(user_id)}
    # )

    logger.info("application.approval.completed", application_id=str(application_id), new_user_id=str(user_id))
    return new_user_profile

async def reject_application(application_id: UUID) -> Dict[str, Any]:
    """Rejects a pending user application."""
    logger.info("application.rejection.started", application_id=str(application_id))
    async with get_db_connection() as conn:
        app_data = await app_db.get_user_application_by_id(conn, application_id)
        if not app_data:
            raise ApplicationNotFoundError()
        if app_data['status'] != 'pending':
            raise ApplicationInvalidStateError(f"Application is not in 'pending' state. Current status: {app_data['status']}")
            
        updated_app = await app_db.update_application_status(conn, application_id, ApplicationStatus.REJECTED)
    logger.info("application.rejection.completed", application_id=str(application_id))
    return updated_app
