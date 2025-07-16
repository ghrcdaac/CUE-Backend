import asyncpg
import os
import logging
from contextlib import asynccontextmanager
from typing import List, Optional, Any, Dict

# Standard logger setup
logger = logging.getLogger(__name__)

# Environment variables should be set in your Lambda configuration
# For v2, PG_HOST should be your RDS PROXY endpoint.
DB_HOST = os.getenv("PG_HOST")
DB_PORT = os.getenv("PG_PORT", 5432)
DB_NAME = os.getenv("PG_DB")
DB_USER = os.getenv("PG_USER")
DB_PASS = os.getenv("PG_PASS")


@asynccontextmanager
async def get_db_connection():
    """
    Provides a single, managed database connection.
    Uses a context manager to ensure the connection is always closed.
    """
    conn = None
    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASS]):
        logger.error("Database environment variables are not fully configured.")
        raise ValueError("Missing database configuration in environment variables.")

    try:
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        logger.debug(f"Connection acquired to {DB_HOST}")
        yield conn
    except asyncpg.PostgresError as e:
        logger.error(f"Database connection error: {e}", exc_info=True)
        # Re-raise the exception to be handled by the calling function
        raise
    finally:
        if conn and not conn.is_closed():
            await conn.close()
            logger.debug(f"Connection to {DB_HOST} closed.")


async def fetch(conn: asyncpg.Connection, sql: str, *params: Any) -> List[asyncpg.Record]:
    """Executes a query and returns a list of all records (like 'fetchall')."""
    try:
        return await conn.fetch(sql, *params)
    except asyncpg.PostgresError as e:
        logger.error(f"Failed to execute fetch query: {sql[:100]}... Error: {e}")
        raise

async def fetchrow(conn: asyncpg.Connection, sql: str, *params: Any) -> Optional[asyncpg.Record]:
    """Executes a query and returns a single record or None (like 'fetchone')."""
    try:
        return await conn.fetchrow(sql, *params)
    except asyncpg.PostgresError as e:
        logger.error(f"Failed to execute fetchrow query: {sql[:100]}... Error: {e}")
        raise

async def fetchval(conn: asyncpg.Connection, sql: str, *params: Any) -> Optional[Any]:
    """Executes a query and returns a single value from a single record."""
    try:
        return await conn.fetchval(sql, *params)
    except asyncpg.PostgresError as e:
        logger.error(f"Failed to execute fetchval query: {sql[:100]}... Error: {e}")
        raise

async def execute(conn: asyncpg.Connection, sql: str, *params: Any) -> str:
    """Executes a command (INSERT, UPDATE, DELETE) and returns the status."""
    try:
        return await conn.execute(sql, *params)
    except asyncpg.PostgresError as e:
        logger.error(f"Failed to execute command: {sql[:100]}... Error: {e}")
        raise