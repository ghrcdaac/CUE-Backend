from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError, DataError
from typing import Tuple, List
import logging

logger = logging.getLogger(__name__)

async def create_cueuser_ngroup_association_in_db(conn: Connection, params: Tuple) -> bool:
    """Associates a cueuser with an ngroup in the database."""
    insert_query = """
        INSERT INTO cueuser_ngroup (cueuser_id, ngroup_id)
        VALUES ($1, $2)
    """
    try:
        await conn.execute(insert_query, *params)
        return True
    except UniqueViolationError as e:
        logger.error(f"Failed to create association due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("The cueuser is already associated with the ngroup.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to create association due to foreign key violation: {e}", exc_info=True)
        raise ValueError("Invalid cueuser_id or ngroup_id provided.")
    except DataError as e:
        logger.error(f"Failed to create association due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating association.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating association: {e}", exc_info=True)
        raise

async def delete_cueuser_ngroup_association_from_db(conn: Connection, params: Tuple) -> bool:
    """Removes the association between a cueuser and an ngroup in the database."""
    delete_query = """
        DELETE FROM cueuser_ngroup
        WHERE cueuser_id = $1 AND ngroup_id = $2
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting association: {e}", exc_info=True)
        raise

async def list_ngroups_for_cueuser_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves all ngroups associated with a cueuser from the database."""
    select_query = """
        SELECT ngroup_id
        FROM cueuser_ngroup
        WHERE cueuser_id = $1
    """
    try:
        results = await conn.fetch(select_query, *params)
        return [result['ngroup_id'] for result in results]
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing ngroups for cueuser: {e}", exc_info=True)
        raise

async def list_cueusers_in_ngroup_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves all cueusers associated with an ngroup from the database."""
    select_query = """
        SELECT cueuser_id
        FROM cueuser_ngroup
        WHERE ngroup_id = $1
    """
    try:
        results = await conn.fetch(select_query, *params)
        return [result['cueuser_id'] for result in results]
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing cueusers in ngroup: {e}", exc_info=True)
        raise