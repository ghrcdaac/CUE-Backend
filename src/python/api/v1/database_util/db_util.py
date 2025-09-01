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
    "total_connections": 0,       # Represents the max_size of the pool
    "active_connections": 0,      # Connections currently executing queries (Used)
    "idle_connections": 0,        # Connections available in the pool (Available)
    "total_acquire_time_ms": 0,
    "acquire_count": 0,
    "last_reset_time": time.time(),
    # Explicitly adding keys as requested, mirroring active/idle
    "pool_used": 0,               # Mirrors active_connections
    "pool_available": 0,          # Mirrors idle_connections
}

_metrics_lock = asyncio.Lock()

async def get_connection_pool(
    min_size: int = int(os.getenv("POOL_MIN_SIZE", "1")),
    max_size: int = int(os.getenv("POOL_MAX_SIZE", "70")),
    max_queries: int = 50000,
    max_inactive_connection_lifetime: float = 300.0,
    setup: Optional[Callable] = None
):
    """
    Creates and returns a connection pool for the V1 API.
    """
    global _connection_pool_metrics
    pool = None
    ssl_mode = os.getenv("DB_SSL_MODE", "require")
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
            setup=setup,
            ssl=ssl_mode
        )
        async with _metrics_lock:
            current_size = pool.get_size()
            _connection_pool_metrics["total_connections"] = max_size
            _connection_pool_metrics["idle_connections"] = current_size
            _connection_pool_metrics["active_connections"] = 0
            _connection_pool_metrics["pool_available"] = _connection_pool_metrics["idle_connections"]
            _connection_pool_metrics["pool_used"] = _connection_pool_metrics["active_connections"]
        return pool
    except Exception as e:
        logger.error(f"Failed to create connection pool: {e}", exc_info=True)
        if pool:
            await pool.close()
        raise

async def setup_connection(conn):
    """Setup function for connections in the pool."""
    if conn.is_closed():
        logger.warning("Attempted to set up a closed connection")
        return
    try:
        pass
    except Exception as e:
        logger.error(f"Error setting up connection: {e}", exc_info=True)
        raise

async def query(pool: asyncpg.pool.Pool, operation: Callable, params: Optional[Tuple] = None, row_mapper: Optional[Callable[[Tuple], T]] = None) -> List[T] | List[Any]:
    """
    Executes a database query using the provided V1 connection pool.
    """
    global _connection_pool_metrics
    acquire_start_time = time.time()
    async with pool.acquire() as conn:
        acquire_end_time = time.time()
        async with _metrics_lock:
            _connection_pool_metrics["active_connections"] += 1
            current_total = pool.get_size()
            _connection_pool_metrics["idle_connections"] = max(0, current_total - _connection_pool_metrics["active_connections"])
            _connection_pool_metrics["total_acquire_time_ms"] += (acquire_end_time - acquire_start_time) * 1000
            _connection_pool_metrics["acquire_count"] += 1
            _connection_pool_metrics["pool_used"] = _connection_pool_metrics["active_connections"]
            _connection_pool_metrics["pool_available"] = _connection_pool_metrics["idle_connections"]

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
               current_total = pool.get_size()
               _connection_pool_metrics["idle_connections"] = max(0, current_total - _connection_pool_metrics["active_connections"])
               _connection_pool_metrics["pool_used"] = _connection_pool_metrics["active_connections"]
               _connection_pool_metrics["pool_available"] = _connection_pool_metrics["idle_connections"]

# Need the pool object to get accurate live counts for available/used
async def get_metrics(pool: Optional[asyncpg.pool.Pool] = None):
    """
    Returns the current connection pool metrics.
    Requires the pool object to get live size information.
    """
    global _connection_pool_metrics
    async with _metrics_lock:
        current_time = time.time()
        elapsed_time = current_time - _connection_pool_metrics["last_reset_time"]
        metrics = _connection_pool_metrics.copy()

        # If pool object is provided, update idle/available based on its current state
        if pool:
            # It's better to get the live count from the pool itself if possible
            # Pool.get_size() = total connections currently in pool (idle + active)
            # Pool.get_idle_size() = total idle connections currently in pool
            # Pool.get_max_size() = configured maximum size
            current_total = pool.get_size()
            current_idle = pool.get_idle_size()
            current_active = current_total - current_idle

            metrics["idle_connections"] = current_idle
            metrics["active_connections"] = current_active
            metrics["pool_available"] = current_idle
            metrics["pool_used"] = current_active
            # Keep total_connections as the configured max_size unless you prefer live count
            # metrics["total_connections"] = current_total # Option to report live total instead of max

        else:
            # Fallback if pool object isn't passed (less accurate for idle/active)
             metrics["idle_connections"] = metrics["total_connections"] - metrics["active_connections"]
             metrics["pool_available"] = metrics["idle_connections"]
             metrics["pool_used"] = metrics["active_connections"]


        metrics["elapsed_time_since_reset"] = elapsed_time
        if metrics["acquire_count"] > 0:
            metrics["average_acquire_time_ms"] = metrics["total_acquire_time_ms"] / metrics["acquire_count"]
        else:
            metrics["average_acquire_time_ms"] = 0

        return metrics

async def reset_metrics():
    """Resets the connection pool metrics."""
    global _connection_pool_metrics
    async with _metrics_lock:
        # Preserve total_connections if it represents max_size, otherwise reset too
        # Assuming we want to keep max_size known after reset
        current_max = _connection_pool_metrics["total_connections"]
        _connection_pool_metrics = {
            "total_connections": current_max, # Keep track of configured max size
            "active_connections": 0,
            "idle_connections": 0, # Will be updated when pool is used or get_metrics(pool) called
            "total_acquire_time_ms": 0,
            "acquire_count": 0,
            "last_reset_time": time.time(),
            "pool_used": 0,
            "pool_available": 0, # Will be updated
        }