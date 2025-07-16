import logging
from typing import Dict, Any

# Import the new, clean connection manager
from ...core.db import get_db_connection, fetchval

logger = logging.getLogger(__name__)

async def get_postgres_connection_stats() -> Dict[str, Any]:
    """
    Retrieves active connection statistics directly from PostgreSQL.

    Note: This shows connections to the database instance itself. For true
    pooling metrics, you should use Amazon CloudWatch for your RDS Proxy.
    """
    sql_query = "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();"
    try:
        # Use the connection manager to safely connect and query
        async with get_db_connection() as conn:
            active_connections = await fetchval(conn, sql_query)
        
        return {
            "source": "PostgreSQL",
            "active_database_connections": active_connections or 0,
            "message": "For detailed proxy metrics (e.g., connection reuse), check AWS CloudWatch."
        }
    except Exception as e:
        logger.error(f"Could not retrieve PostgreSQL connection stats: {e}")
        return {
            "source": "PostgreSQL",
            "error": "Failed to retrieve connection stats."
        }