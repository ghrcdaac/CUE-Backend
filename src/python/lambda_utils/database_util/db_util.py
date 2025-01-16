import asyncpg
import os
from typing import Callable, Any, List, Tuple, Optional, Type, TypeVar, Generic

# Define a generic type variable for the return type of the row mapper
T = TypeVar('T')

async def get_connection_pool():
    """Creates and returns a connection pool."""
    return await asyncpg.create_pool(
        database=os.getenv('PG_DB'),
        user=os.getenv('PG_USER'),
        password=os.getenv('PG_PASS'),
        host=os.getenv('PG_HOST'),
        port=os.getenv('PG_PORT')
    )

async def query(pool: asyncpg.pool.Pool, operation: Callable, params: Tuple = (), row_mapper: Optional[Callable[[Tuple], T]] = None) -> List[T] | List[Any]:
    """
    Executes a database query using the provided connection pool.

    Args:
        pool: The asyncpg connection pool.
        operation: The database operation function to execute (e.g., from egress_db, scanning_db, etc.).
        params: The parameters to pass to the operation function.
        row_mapper: An optional function to map each result row to a desired type (e.g., a Pydantic model).

    Returns:
        A list of mapped objects (if row_mapper is provided) or a list of raw database rows.
    """
    async with pool.acquire() as conn:
        try:
            result = await operation(conn, params)
            if result is not None and row_mapper:  # Check if result is not None
                return [row_mapper(row) for row in result]
            else:
                return result if result is not None else []  # Return an empty list if result is None
        except Exception as e:
            print(f"Error executing query: {e}")
            raise