# ==============================================================================
# File: src/python/api/v2/utils/user_application.py (Fixed)
# Purpose: Contains the business logic for the user application workflow.
# Fix: Ensure all functions that return database records convert them to dicts
#      before returning, to prevent Pydantic validation errors.
# ==============================================================================
from uuid import UUID
from typing import List, Dict, Any, Optional
import structlog

from core.db import get_db_connection
from v2.database_util import user_application as app_db
from v2.type_util.user_application import UserApplicationCreate, ApplicationStatus, AccountType
from v2.utils.cueuser import create_new_user
from v2.utils.auth import KeycloakClient

logger = structlog.get_logger(__name__)

class ApplicationNotFoundError(Exception):
    pass

class ApplicationInvalidStateError(Exception):
    pass

async def submit_application(app_data: UserApplicationCreate) -> Dict[str, Any]:
    """Submits a new user application."""
    async with get_db_connection() as conn:
        new_app_record = await app_db.create_user_application(conn, app_data)
    logger.info("application.submitted", application_id=str(new_app_record['id']))
    # --- CHANGE: Convert record to dict ---
    return dict(new_app_record)

async def get_application(application_id: UUID) -> Dict[str, Any]:
    """Retrieves a single application."""
    async with get_db_connection() as conn:
        app_record = await app_db.get_user_application_by_id(conn, application_id)
    if not app_record:
        raise ApplicationNotFoundError()
    # --- CHANGE: Convert record to dict ---
    return dict(app_record)

async def list_applications(ngroup_id: Optional[UUID] = None, status: Optional[ApplicationStatus] = None) -> List[Dict[str, Any]]:
    """Lists all applications based on optional filters."""
    async with get_db_connection() as conn:
        app_records = await app_db.list_user_applications(conn, ngroup_id, status)
    # --- CHANGE: Convert list of records to list of dicts ---
    return [dict(record) for record in app_records]

async def approve_application(application_id: UUID, role_id: UUID, keycloak_client: KeycloakClient) -> Dict[str, Any]:
    """
    Approves an application, which triggers the creation of the user in Keycloak
    and the local database. This is a critical transactional process.
    """
    logger.info("application.approval.started", application_id=str(application_id))
    async with get_db_connection() as conn:
        app_data = await app_db.get_user_application_by_id(conn, application_id)
        if not app_data:
            raise ApplicationNotFoundError()
        if app_data['status'] != 'pending':
            raise ApplicationInvalidStateError(f"Application is not in 'pending' state. Current status: {app_data['status']}")

        ngroup_ids_to_assign = None
        provider_ids_to_assign = None

        if app_data['account_type'] == AccountType.DAAC.value:
            ngroup_ids_to_assign = [app_data['ngroup_id']]
        elif app_data['account_type'] == AccountType.PROVIDER.value:
            ngroup_ids_to_assign = [app_data['ngroup_id']]
            provider_ids_to_assign = [app_data['provider_id']]
        
        new_user = await create_new_user(
            email=app_data['email'],
            name=app_data['name'],
            username=app_data['username'],
            role_id=role_id,
            ngroup_ids=ngroup_ids_to_assign,
            provider_ids=provider_ids_to_assign,
            edpub_id=app_data['edpub_id'],
            keycloak_client=keycloak_client
        )
        
        await app_db.update_application_status(conn, application_id, ApplicationStatus.APPROVED)
        logger.info("application.approval.completed", application_id=str(application_id), new_user_id=str(new_user['id']))
        return new_user

async def reject_application(application_id: UUID) -> Dict[str, Any]:
    """Rejects a pending user application."""
    logger.info("application.rejection.started", application_id=str(application_id))
    async with get_db_connection() as conn:
        app_data = await app_db.get_user_application_by_id(conn, application_id)
        if not app_data:
            raise ApplicationNotFoundError()
        if app_data['status'] != 'pending':
            raise ApplicationInvalidStateError(f"Application is not in 'pending' state. Current status: {app_data['status']}")
            
        updated_app_record = await app_db.update_application_status(conn, application_id, ApplicationStatus.REJECTED)
    logger.info("application.rejection.completed", application_id=str(application_id))
    # --- CHANGE: Convert record to dict ---
    return dict(updated_app_record)
