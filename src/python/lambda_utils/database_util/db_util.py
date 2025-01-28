import asyncpg
import os
from typing import Callable, Any, List, Tuple, Optional, TypeVar
import logging
import time
import asyncio

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Global variable to store metrics
_connection_pool_metrics = {
    "total_connections": 0,
    "active_connections": 0,
    "idle_connections": 0,
    "total_acquire_time_ms": 0,
    "acquire_count": 0,
    "last_reset_time": time.time(),
}

_metrics_lock = asyncio.Lock()

async def get_connection_pool(
    min_size: int = int(os.getenv("POOL_MIN_SIZE", "1")),
    max_size: int = int(os.getenv("POOL_MAX_SIZE", "10")),
    max_queries: int = 50000,
    max_inactive_connection_lifetime: float = 300.0,
    setup: Optional[Callable] = None
):
    """
    Creates and returns a connection pool with configurable parameters.

    Args:
        min_size: Minimum number of connections in the pool.
        max_size: Maximum number of connections in the pool.
        max_queries: Number of queries after which a connection is closed and replaced with a new one.
        max_inactive_connection_lifetime: Maximum time (in seconds) after which an inactive connection is closed.
        setup: An optional async function to setup each connection when its created.
    """
    global _connection_pool_metrics

    pool = None  # Initialize pool to None outside the try block
    try:
        pool = await asyncpg.create_pool(
            database=os.getenv('PG_DB'),
            user=os.getenv('PG_USER'),
            password=os.getenv('PG_PASS'),
            host=os.getenv('PG_HOST'),
            port=os.getenv('PG_PORT'),
            min_size=min_size,
            max_size=max_size,
            max_queries=max_queries,
            max_inactive_connection_lifetime=max_inactive_connection_lifetime,
            setup=setup
        )
        # Update total connections based on successful pool creation
        async with _metrics_lock:
            _connection_pool_metrics["total_connections"] = max_size
        return pool
    except Exception as e:
        logger.error(f"Failed to create connection pool: {e}", exc_info=True)
        if pool:
            await pool.close()
        raise

async def setup_connection(conn):
    """Setup function for connections in the pool."""
    global _connection_pool_metrics
    async with _metrics_lock:
        _connection_pool_metrics["total_connections"] += 1

    # Check if the connection is already closed
    if conn.is_closed():
        logger.warning("Attempted to set up a closed connection")
        return

    # Proceed with setup if the connection is open
    try:
        # set custom connection properties here if needed.
        pass
    except Exception as e:
        logger.error(f"Error setting up connection: {e}", exc_info=True)
        raise

async def query(pool: asyncpg.pool.Pool, operation: Callable, params: Optional[Tuple] = None, row_mapper: Optional[Callable[[Tuple], T]] = None) -> List[T] | List[Any]:
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
        acquire_end_time = time.time()
        async with _metrics_lock:
            _connection_pool_metrics["active_connections"] += 1
            _connection_pool_metrics["idle_connections"] = _connection_pool_metrics["total_connections"] - _connection_pool_metrics["active_connections"]
            _connection_pool_metrics["total_acquire_time_ms"] += (acquire_end_time - acquire_start_time) * 1000
            _connection_pool_metrics["acquire_count"] += 1
        try:
            async with conn.transaction():
                if params:
                    result = await operation(conn, params)
                else:
                    result = await operation(conn)
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

async def get_metrics():
    """Returns the current connection pool metrics."""
    global _connection_pool_metrics
    async with _metrics_lock:
        current_time = time.time()
        elapsed_time = current_time - _connection_pool_metrics["last_reset_time"]
        metrics = _connection_pool_metrics.copy()
        metrics["elapsed_time_since_reset"] = elapsed_time
        if metrics["acquire_count"] > 0:
            metrics["average_acquire_time_ms"] = metrics["total_acquire_time_ms"] / metrics["acquire_count"]
        else:
            metrics["average_acquire_time_ms"] = 0
        # Update idle_connections based on current state
        metrics["idle_connections"] = metrics["total_connections"] - metrics["active_connections"]
        return metrics

async def reset_metrics():
    """Resets the connection pool metrics."""
    global _connection_pool_metrics
    async with _metrics_lock:
        _connection_pool_metrics = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "total_acquire_time_ms": 0,
            "acquire_count": 0,
            "last_reset_time": time.time(),
        }