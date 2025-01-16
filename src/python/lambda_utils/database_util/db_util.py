import psycopg
import os
from typing import Callable, Any, List, Tuple, Optional

def get_connection():
    conn = psycopg.connect(
        f"dbname={os.getenv('PG_DB')} user={os.getenv('PG_USER')} "
        f"password={os.getenv('PG_PASS')} host={os.getenv('PG_HOST')}"
    )
    return conn

def _map_row_to_egress(row: Tuple) -> "EgressReturn":
    """Helper function to map a database row to an EgressReturn object."""
    from lambda_utils.type_util.egress import EgressReturn  # Import here to avoid circular imports
    id, type, path, config, ngroup_id = row
    return EgressReturn(id=id, type=type, path=path, config=config, ngroup_id=ngroup_id)

def query(operation: Callable, params: Tuple = (), row_mapper: Optional[Callable] = None) -> List[Any]:
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            operation(cur, params)
            if cur.description:  # Check if the query returns data
                rows = cur.fetchall()
                if row_mapper:
                    return [row_mapper(row) for row in rows]
                else:
                    return rows
            else:
                return []
    except Exception as e:
        print(f"Error executing query: {e}")
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        if conn:
            conn.close()