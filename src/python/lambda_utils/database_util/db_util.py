import asyncpg
import os
from typing import Callable, Any, List, Tuple, Optional, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Global variable to store metrics
_connection_pool_metrics = {
    "total_connections": 0,
    "active_connections": 0,
    "idle_connections": 0,
    "total_acquire_time_ms": 0,  # Total time spent acquiring connections
    "acquire_count": 0,  # Number of times a connection was acquired
    "last_reset_time": time.time(),
}

_metrics_lock = asyncio.Lock()  # Lock for thread-safe metrics updates

async def get_connection_pool():
    """Creates and returns a connection pool."""
    pool = await asyncpg.create_pool(
            database=os.getenv('PG_DB'),
            user=os.getenv('PG_USER'),
            password=os.getenv('PG_PASS'),
            host=os.getenv('PG_HOST'),
            port=os.getenv('PG_PORT'),
            setup=setup_connection
    )
    return pool

async def setup_connection(conn):
    """Setup function for connections in the pool."""
    global _connection_pool_metrics
    async with _metrics_lock:
        _connection_pool_metrics["total_connections"] += 1

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
    global _connection_pool_metrics
    acquire_start_time = time.time()
    async with pool.acquire() as conn:
        async with _metrics_lock:
            _connection_pool_metrics["active_connections"] += 1
            _connection_pool_metrics["idle_connections"] = _connection_pool_metrics["total_connections"] - _connection_pool_metrics["active_connections"]
            _connection_pool_metrics["total_acquire_time_ms"] += (time.time() - acquire_start_time) * 1000
            _connection_pool_metrics["acquire_count"] += 1
        try:
            async with conn.transaction():
                result = await operation(conn, params)
                if result is not None and row_mapper:
                    return [row_mapper(row) for row in result]
                else:
                    return result if result is not None else []
        except Exception as e:
            logger.error(f"Error executing query: {e}", exc_info=True)
            raise
        finally:
            async with _metrics_lock:
                _connection_pool_metrics["active_connections"] -= 1
                _connection_pool_metrics["idle_connections"] = _connection_pool_metrics["total_connections"] - _connection_pool_metrics["active_connections"]


def get_metrics():
    """Returns the current connection pool metrics."""
    global _connection_pool_metrics
    current_time = time.time()
    elapsed_time = current_time - _connection_pool_metrics["last_reset_time"]
    metrics = _connection_pool_metrics.copy()
    metrics["elapsed_time_since_reset"] = elapsed_time
    if metrics["acquire_count"] > 0:
        metrics["average_acquire_time_ms"] = metrics["total_acquire_time_ms"] / metrics["acquire_count"]
    else:
        metrics["average_acquire_time_ms"] = 0
    return metrics

def reset_metrics():
    """Resets the connection pool metrics."""
    global _connection_pool_metrics
    _connection_pool_metrics = {
        "total_connections": 0,
        "active_connections": 0,
        "idle_connections": 0,
        "total_acquire_time_ms": 0,
        "acquire_count": 0,
        "last_reset_time": time.time(),
    }