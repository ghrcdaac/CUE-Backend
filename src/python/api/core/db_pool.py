import asyncpg
import os
import structlog

logger = structlog.get_logger(__name__)

# This global variable will hold the connection pool after it's initialized.
db_pool = None

async def get_database_pool():
    """
    Initializes and returns a reusable, shared database connection pool.
    This function is idempotent; it creates the pool on the first call and
    returns the existing pool on subsequent calls within the same Lambda container.
    """
    global db_pool
    # If the pool already exists and is connected, return it immediately.
    if db_pool and not db_pool._closed:
        return db_pool

    try:
        logger.info("db.pool.initializing")
        # The 'await' is now correctly inside an async function.
        db_pool = await asyncpg.create_pool(
            host=os.getenv("PG_HOST"),
            port=os.getenv("PG_PORT", 5432),
            database=os.getenv("PG_DB"),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASS"),
            ssl=os.getenv("DB_SSL_MODE", "require"),
            min_size=1,
            max_size=3,
            timeout=8
        )
        logger.info("db.pool.initialized_successfully")
        return db_pool
    except Exception as e:
        logger.critical("db.pool.initialization_failed", error=str(e), exc_info=True)
        db_pool = None # Ensure pool is None on failure
        raise # Re-raise the exception to fail the invocation and trigger retries.

