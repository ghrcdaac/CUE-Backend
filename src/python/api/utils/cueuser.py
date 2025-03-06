import os
import uuid
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import cueuser as cueuser_db

from typing import List, Optional, TYPE_CHECKING, Dict
from uuid import UUID
import logging
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError
from fastapi import Depends

from lambda_utils.type_util.cueuser import *  # Import the corrected type definitions

logger = logging.getLogger(__name__)


async def get_cognito_client():
    return boto3.client('cognito-idp', region_name=os.environ.get('AWS_REGION'))

class CueuserNotFoundError(Exception):
    def __init__(self, cueuser_id: UUID = None, email: str = None, cueusername: str = None, name: str = None,
                 edpub_id: str = None, ngroup_id: UUID = None):
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
        elif ngroup_id:
            message = f"Cueuser not found with ngroup_id: {ngroup_id}"
        else:
            message = "Cueuser not found"
        super().__init__(message)
        self.cueuser_id = cueuser_id
        self.email = email
        self.cueusername = cueusername
        self.name = name
        self.edpub_id = edpub_id
        self.ngroup_id = ngroup_id


async def create_cueuser(cueuser: CueuserCreate, cognito_client=Depends(get_cognito_client)) -> CueuserReturn:
    """Creates a new cueuser record and a Cognito user, and associations."""
    pool: Pool = await get_connection_pool()
    conn = await pool.acquire()

    try:
        async with conn.transaction():
            # --- 1. Create user in Cognito ---
            try:
                response = cognito_client.admin_create_user(
                    UserPoolId=os.environ.get('POOL_ID'),
                    Username=cueuser.cueusername,  # Use cueusername
                    UserAttributes=[
                        {'Name': 'email', 'Value': cueuser.email},
                        {'Name': 'name', 'Value': cueuser.name},
                        # Add other Cognito attributes if needed
                    ],
                    DesiredDeliveryMediums=['EMAIL']
                )

                cognito_uuid = None
                for attr in response['User']['Attributes']:
                    if attr['Name'] == 'sub':
                        cognito_uuid = attr['Value']
                        break

                if cognito_uuid is None:
                    raise ValueError("Cognito user created, but 'sub' attribute (UUID) not found.")

            except ClientError as e:
                logger.error(f"Cognito error: {e}", exc_info=True)
                if e.response['Error']['Code'] == 'UsernameExistsException':
                    raise ValueError(
                        f"User with username '{cueuser.cueusername}' already exists in Cognito.") from e
                else:
                    raise ValueError(f"Failed to create Cognito user: {e}") from e

            # --- 2. Create user in the database ---
            #  Use cognito_uuid as the primary key!
            params = (cognito_uuid, cueuser.email, cueuser.name, datetime.now(timezone.utc), cueuser.cueusername,
                      cueuser.edpub_id)
            try:
                result = await cueuser_db.create_cueuser_in_db(conn, params)
                if not result:
                    raise ValueError("Failed to insert cueuser into database")
                # Use cognito_uuid directly, no separate id
                db_user_result = result[0]
                db_user = CueuserReturn(
                    id=db_user_result['id'],
                    email=db_user_result['email'],
                    name=db_user_result['name'],
                    cueusername=db_user_result['cueusername'],
                    edpub_id=db_user_result['edpub_id'],
                    registered=db_user_result['registered']
                )

                # --- 3. Create associations (if provided) ---
                if cueuser.ngroup_id:
                    await cueuser_db.create_cueuser_ngroup_association_in_db(conn, db_user.id, cueuser.ngroup_id)
                    db_user.ngroup_id = cueuser.ngroup_id
                if cueuser.provider_id:
                    await cueuser_db.create_cueuser_provider_association_in_db(conn, db_user.id,
                                                                                cueuser.provider_id)
                    db_user.provider_id = cueuser.provider_id
                if cueuser.role_id:
                    await cueuser_db.create_cueuser_role_association_in_db(conn, db_user.id, cueuser.role_id)
                    db_user.role_id = cueuser.role_id
                # Fetch role details immediately

                # --- 4. Fetch and Return COMPLETE data ---
                # Fetch complete user information, including associations
                # providing a dummy ngroup_id.
                complete_user_data = await cueuser_db.get_cueuser_from_db(conn, (
                db_user.id, cueuser.ngroup_id if cueuser.ngroup_id else uuid.uuid4()))  # Use a dummy UUID if ngroup_id is None

                if not complete_user_data:
                    # This *should* never happen, given the transaction, but it's good to check.
                    raise ValueError("Failed to retrieve newly created cueuser.")
                return CueuserReturn.from_db_row(complete_user_data[0])


            except Exception as e:
                logger.error(f"Database error: {e}", exc_info=True)
                # Rollback Cognito user creation
                try:
                    cognito_client.admin_delete_user(UserPoolId=os.environ.get('POOL_ID'), Username=cognito_uuid)
                    logger.info(f"Deleted Cognito user {cognito_uuid} due to database error.")
                except ClientError as delete_e:
                    logger.error(f"Error deleting Cognito user after database failure: {delete_e}", exc_info=True)
                    #  Decide: Re-raise the original exception, or a combined exception?
                raise  # Re-raise the original database exception

    except Exception as e:
        logger.error(f"Error creating cueuser: {e}", exc_info=True)
        raise
    finally:
        await pool.release(conn)

async def get_cueuser(cueuser_id: UUID, ngroup_id: UUID) -> CueuserReturn | None:
    """Retrieves a cueuser record by its ID."""
    pool: Pool = await get_connection_pool()
    params = (cueuser_id, ngroup_id)
    try:
        result = await query(pool, cueuser_db.get_cueuser_from_db, params, row_mapper=CueuserReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise CueuserNotFoundError(cueuser_id=cueuser_id, ngroup_id=ngroup_id)
    finally:
        await pool.close()


async def get_user_ngroup_id(cueuser_id: UUID) -> UUID | None:
    """Retrieves the ngroup_id for a given cueuser_id.  Helper function."""
    pool: Pool = await get_connection_pool()
    async with pool.acquire() as conn:
        try:
            result = await conn.fetchval("SELECT ngroup_id FROM cueuser_ngroup WHERE cueuser_id = $1", cueuser_id)
            return result
        except Exception as e:
            logger.error(f"Error getting ngroup_id: {e}", exc_info=True)
            raise

async def update_cueuser(cueuser_id: UUID, cueuser_update: CueuserUpdate) -> CueuserReturn:
    """Updates a cueuser and its associations. Handles partial updates correctly."""
    pool: Pool = await get_connection_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Get the *current* ngroup_id (before any updates).
            current_ngroup_id = await get_user_ngroup_id(cueuser_id)
            if current_ngroup_id is None:
                raise ValueError("Cannot update user: Current ngroup_id association not found.")

            # 2. Update associations (conditionally and simplified).
            update_payload = cueuser_update.model_dump(exclude_unset=True)

            if 'ngroup_id' in update_payload:
                await cueuser_db.update_cueuser_ngroup_association_in_db(conn, cueuser_id, cueuser_update.ngroup_id)
            if 'provider_id' in update_payload:
                await cueuser_db.update_cueuser_provider_association_in_db(conn, cueuser_id, cueuser_update.provider_id)
            if 'role_id' in update_payload:
                await cueuser_db.update_cueuser_role_association_in_db(conn, cueuser_id, cueuser_update.role_id)

            # 3. Prepare update data for the 'cueuser' table.
            update_data = {
                k: v for k, v in cueuser_update.model_dump().items()
                if k not in ['ngroup_id', 'provider_id', 'role_id'] and v is not None
            }

            # 4. Update the 'cueuser' record itself (if needed).
            if update_data:
                updated_user_row = await cueuser_db.update_cueuser_in_db(conn, cueuser_id, update_data)
                if not updated_user_row:
                    raise CueuserNotFoundError(cueuser_id=cueuser_id)
            else:
                updated_user_row = await conn.fetchrow("SELECT * FROM cueuser where id = $1", cueuser_id)
                if not updated_user_row:
                    raise CueuserNotFoundError(cueuser_id=cueuser_id)

            # 5. Determine the *final* ngroup_id.
            final_ngroup_id = cueuser_update.ngroup_id if 'ngroup_id' in update_payload else current_ngroup_id

            # 6. Fetch and return the complete, updated user data.
            complete_user_data = await cueuser_db.get_cueuser_from_db(conn, (cueuser_id, final_ngroup_id))

            if not complete_user_data:
                raise CueuserNotFoundError(cueuser_id=cueuser_id)

            return CueuserReturn.from_db_row(complete_user_data[0])

async def delete_cueuser(cueuser_id: UUID, ngroup_id: UUID, cognito_client=Depends(get_cognito_client)) -> bool:
    """Deletes a cueuser record and its associations, then the Cognito user."""
    pool: Pool = await get_connection_pool()
    conn = await pool.acquire()
    try:
        async with conn.transaction():
            # 1. Fetch the user data (including username for Cognito) *before* any deletions.
            cueuser_data = await cueuser_db.get_cueuser_from_db(conn, (cueuser_id, ngroup_id))  # Pass both IDs
            if not cueuser_data:
                raise CueuserNotFoundError(cueuser_id=cueuser_id, ngroup_id=ngroup_id)
            username = cueuser_data[0]['cueusername']

            # 2. Delete associations.
            try:
                await cueuser_db.delete_cueuser_ngroup_association_in_db(conn, cueuser_id,
                                                                        ngroup_id)
            except Exception as e:
                logger.warning(f"Error deleting cueuser_ngroup association: {e}")
            try:
                if cueuser_data[0]['provider_id']:
                    await cueuser_db.delete_cueuser_provider_association_in_db(conn, cueuser_id,
                                                                                cueuser_data[0]['provider_id'])
            except Exception as e:
                logger.warning(f"Error deleting cueuser_provider association: {e}")
            try:
                if cueuser_data[0]['role_id']:
                    await cueuser_db.delete_cueuser_role_association_in_db(conn, cueuser_id,
                                                                            cueuser_data[0]['role_id'])
            except Exception as e:
                logger.warning(f"Error deleting cueuser_role association: {e}")

            # 3. Delete the cueuser record.
            result = await cueuser_db.delete_cueuser_from_db(conn, (cueuser_id,))
            if not result:
                raise CueuserNotFoundError(cueuser_id=cueuser_id)

            # 4. Delete the Cognito user.
            try:
                cognito_client.admin_delete_user(UserPoolId=os.environ.get('POOL_ID'),
                                                 Username=username)
            except ClientError as e:
                logger.error(f"Error deleting Cognito user: {e}", exc_info=True)
                raise

            return result

    except Exception as e:
        logger.error(f"Error deleting cueuser: {e}", exc_info=True)
        raise
    finally:
        await pool.release(conn)


async def list_cueusers(ngroup_id: UUID) -> List[CueuserReturn]:
    """Retrieves all cueuser records."""
    pool: Pool = await get_connection_pool()
    try:
        results = await query(pool, cueuser_db.list_cueusers_from_db, (ngroup_id,),
                              row_mapper=CueuserReturn.from_db_row)
        return results
    finally:
        await pool.close()


async def get_cueuser_by_lookup(
        ngroup_id: UUID,
        email: Optional[str] = None,
        cueusername: Optional[str] = None,
        name: Optional[str] = None,
        edpub_id: Optional[str] = None
 ) -> CueuserReturn | None:
    """Retrieves a cueuser record by email, username, name, or edpub_id."""
    pool: Pool = await get_connection_pool()
    if not any([email, cueusername, name, edpub_id]):
        raise ValueError("Must provide at least one lookup parameter.")
    params = (email, cueusername, name, edpub_id, ngroup_id)

    try:
        result = await query(pool, cueuser_db.get_cueuser_by_lookup_from_db, params,
                             row_mapper=CueuserReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise CueuserNotFoundError(email=email, cueusername=cueusername, name=name, edpub_id=edpub_id,
                                     ngroup_id=ngroup_id)
    finally:
        await pool.close()


async def get_cueuser_role(cueuser_id: UUID) -> CueuserRoleReturn:
    pool: Pool = await get_connection_pool()
    try:
        result = await cueuser_db.get_cueuser_role_from_db(pool, cueuser_id)
        if not result:
            raise CueuserNotFoundError(cueuser_id=cueuser_id)
        return CueuserRoleReturn.model_validate(result)
    finally:
        await pool.close()