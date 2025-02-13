import os
import uuid
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import cueuser as cueuser_db
from lambda_utils.type_util.cueuser import CueuserCreate, CueuserReturn, CueuserUpdate, CueuserAuth
# Additional imports
from typing import List, Optional
from uuid import UUID
import logging
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError
from utils import provider
from lambda_utils.type_util.cueuser_provider import CueuserProviderCreate
from lambda_utils.type_util.role_privilege import RolePrivilegeCreate

from lambda_utils.type_util.cueuser_ngroup import CueuserNgroupCreate  
from lambda_utils.type_util.cueuser_role import CueuserRoleCreate

logger = logging.getLogger(__name__)
_PoolId = os.environ.get('POOL_ID')
_ClientId = os.environ.get('CLIENT_ID')
_Region = os.environ.get('AWS_REGION')

class CueuserNotFoundError(Exception):
    def __init__(self, cueuser_id: UUID = None, email: str = None, cueusername: str = None, name: str = None, edpub_id: str = None):
        if cueuser_id:
            message = f"Cueuser not found with ID: {cueuser_id}"
        elif email:
            message = f"Cueuser not found with email: {email}"
        elif cueusername:
            message = f"Cueuser not found with username: {cueusername}"
        elif name:
            message = f"Cueuser not found with name: {name}"
        elif edpub_id:
            message = f"Cueuser not found with edpub_id: {edpub_id}"
        else:
            message = "Cueuser not found"
        super().__init__(message)
        self.cueuser_id = cueuser_id
        self.email = email
        self.cueusername = cueusername
        self.name = name
        self.edpub_id = edpub_id

logger = logging.getLogger(__name__)

class CueuserNotFoundError(Exception):
    def __init__(self, cueuser_id: UUID = None, email: str = None, cueusername: str = None, name: str = None, edpub_id: str = None):
        if cueuser_id:
            message = f"Cueuser not found with ID: {cueuser_id}"
        elif email:
            message = f"Cueuser not found with email: {email}"
        elif cueusername:
            message = f"Cueuser not found with username: {cueusername}"
        elif name:
            message = f"Cueuser not found with name: {name}"
        elif edpub_id:
            message = f"Cueuser not found with edpub_id: {edpub_id}"
        else:
            message = "Cueuser not found"
        super().__init__(message)
        self.cueuser_id = cueuser_id
        self.email = email
        self.cueusername = cueusername
        self.name = name
        self.edpub_id = edpub_id

_PoolId = os.environ.get('POOL_ID')
_ClientId = os.environ.get('CLIENT_ID')
_Region = os.environ.get('AWS_REGION')

async def create_cueuser(cueuser: CueuserCreate) -> CueuserReturn:
    """Creates a new cueuser record and a Cognito user."""
    pool: Pool = await get_connection_pool()
    conn = await pool.acquire()  # Acquire connection here

    try:
        async with conn.transaction():  # Use a transaction
            # --- 1. Create user in Cognito ---
            cognito_client = boto3.client('cognito-idp', region_name=_Region)
            try:
                response = cognito_client.admin_create_user(
                    UserPoolId=_PoolId,
                    Username=cueuser.cueusername,  # Use cueusername as username in Cognito
                    UserAttributes=[
                        {'Name': 'email', 'Value': cueuser.email},
                        {'Name': 'name', 'Value': cueuser.name},
                        # Add any other *required* Cognito attributes here
                    ],
                    DesiredDeliveryMediums=['EMAIL']
                )

                cognito_uuid = response['User']['Username'] #This is UUID
                # --- Get Cognito UUID from response ---
                cognito_uuid = None
                for attr in response['User']['Attributes']:
                    if attr['Name'] == 'sub':
                        cognito_uuid = attr['Value']
                        break  # Exit loop once found

                if cognito_uuid is None:
                    # Extremely unlikely, but handle it just in case.
                    raise ValueError("Cognito user created, but 'sub' attribute (UUID) not found in response.")


            except cognito_client.exceptions.UsernameExistsException:
                await pool.release(conn) #release the connection
                raise ValueError(f"User with email '{cueuser.email}' already exists in Cognito.")
            except cognito_client.exceptions.InvalidParameterException as e:
                await pool.release(conn) #release the connection
                raise ValueError(f"Invalid parameters for Cognito user creation: {e}")
            except Exception as e:
                await pool.release(conn) #release the connection
                logger.error(f"Error creating Cognito user: {e}", exc_info=True)
                raise  # Re-raise the exception to be handled by FastAPI

            # --- 2. Create user in the database ---
            # Use the Cognito-generated UUID as the cueuser.id
            params = (cognito_uuid, cueuser.email, cueuser.name, datetime.now(timezone.utc), cueuser.cueusername, cueuser.edpub_id)
            try:
                result = await cueuser_db.create_cueuser_in_db(conn, params)
                if not result: #Added a condition to check for empty result.
                    raise ValueError("Failed to insert cueuser into database")
                db_user = CueuserReturn.from_db_row(result[0]) # result[0] as it always returns a list

                 # --- 3. Create associations (ngroup, role, provider) ---
                if cueuser.ngroup_id:
                    from . import cueuser_ngroup  # Avoid circular imports
                    await cueuser_ngroup.create_cueuser_ngroup_association(CueuserNgroupCreate(cueuser_id=db_user.id, ngroup_id=cueuser.ngroup_id))

                if cueuser.role_id:
                    from . import cueuser_role # Avoid circular imports
                    await cueuser_role.create_cueuser_role_association(CueuserRoleCreate(cueuser_id=db_user.id, role_id=cueuser.role_id))

                if cueuser.account_type == "provider" and cueuser.provider_id:
                    from . import cueuser_provider # Avoid circular imports
                    await cueuser_provider.create_cueuser_provider_association(CueuserProviderCreate(cueuser_id=db_user.id, provider_id=cueuser.provider_id))


                return db_user  # Return the new CueuserReturn object

            except Exception as e:
                logger.error(f"Error creating cueuser in database: {e}", exc_info=True)
                # If database insert fails, delete the Cognito user.  IMPORTANT!
                try:
                    cognito_client.admin_delete_user(UserPoolId=_PoolId, Username=cognito_uuid)
                    logger.info(f"Deleted Cognito user {cognito_uuid} due to database error.")
                except Exception as delete_e:
                    logger.error(f"Error deleting Cognito user after database failure: {delete_e}", exc_info=True)
                    # Decide if you want to re-raise here, or just log.  A failure
                    # to delete the Cognito user is very bad.
                raise  # Re-raise original exception
    except Exception as e:  # Catch *any* exception

        logger.error(f"Error creating cueuser: {e}", exc_info=True)
        raise
    finally:
        await pool.release(conn)  # *Always* release the connection.


async def get_cueuser(cueuser_id: UUID) -> CueuserReturn | None:
    """Retrieves a cueuser record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (cueuser_id,)
    try:
        result = await query(pool, cueuser_db.get_cueuser_from_db, params, row_mapper=CueuserReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise CueuserNotFoundError(cueuser_id=cueuser_id)
    except Exception as e:
        logger.error(f"Error getting cueuser: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def update_cueuser(cueuser_id: UUID, cueuser_update: CueuserUpdate) -> CueuserReturn | None:
    """Updates an existing cueuser record."""
    pool: Pool = await get_connection_pool()
    update_fields = {k: v for k, v in cueuser_update.model_dump().items() if v is not None}
    if not update_fields:
        return await get_cueuser(cueuser_id)

    params = (update_fields, cueuser_id)
    try:
        result = await query(pool, cueuser_db.update_cueuser_in_db, params, row_mapper=CueuserReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise CueuserNotFoundError(cueuser_id=cueuser_id)
    except Exception as e:
        logger.error(f"Error updating cueuser: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def delete_cueuser(cueuser_id: UUID) -> bool:
    """Deletes a cueuser record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (cueuser_id,)
    try:
        result = await query(pool, cueuser_db.delete_cueuser_from_db, params)
        if not result:
            raise CueuserNotFoundError(cueuser_id=cueuser_id)
        return result
    except Exception as e:
        logger.error(f"Error deleting cueuser: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def list_cueusers() -> List[CueuserReturn]:
    """Retrieves all cueuser records."""
    pool: Pool = await get_connection_pool()
    try:
        results = await query(pool, cueuser_db.list_cueusers_from_db, row_mapper=CueuserReturn.from_db_row)
        return results
    except Exception as e:
        logger.error(f"Error listing cueusers: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_cueuser_by_lookup(
    email: Optional[str] = None,
    cueusername: Optional[str] = None,
    name: Optional[str] = None,
    edpub_id: Optional[str] = None
) -> CueuserReturn | None:
    """Retrieves a cueuser record by email, username, name, or edpub_id."""
    if not email and not cueusername and not name and not edpub_id:
        raise ValueError("Must provide at least one of email, username, name, or edpub_id")

    pool: Pool = await get_connection_pool()
    params = (email, cueusername, name, edpub_id)
    try:
        result = await query(pool, cueuser_db.get_cueuser_by_lookup_from_db, params, row_mapper=CueuserReturn.from_db_row)
        if result:
             return result[0]
        else:
            if email:
               raise CueuserNotFoundError(email=email)
            elif cueusername:
                raise CueuserNotFoundError(cueusername=cueusername)
            elif name:
                raise CueuserNotFoundError(name=name)
            else:
                raise CueuserNotFoundError(edpub_id=edpub_id)
    except Exception as e:
        logger.error(f"Error during cueuser lookup: {e}", exc_info=True)
        raise
    finally:
        await pool.close()

async def get_cueuser_by_username(username: str) -> Optional[CueuserAuth]:  # Corrected return type
    """Retrieves a cueuser by username."""
    pool: Pool = await get_connection_pool()
    try:
        result = await query(pool, cueuser_db.get_cueuser_by_username, (username,), row_mapper=CueuserAuth.from_db_row) # Pass username in a tuple
        if result:
            return result[0]  # Return the first result (should only be one)
        return None  # Return None if no user is found
    except Exception as e:
        logger.error(f"Failed to retrieve cueuser by username: {e!r}", exc_info=True)
        raise
    finally:
        await pool.close()