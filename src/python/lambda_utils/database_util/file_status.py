from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError, DataError
from typing import Tuple, List, Optional, Dict, Any
from uuid import UUID
import logging


logger = logging.getLogger(__name__)

async def _build_metrics_query_parts(
    ngroup_id: UUID,
    optional_filters: Dict[str, Any],
    mandatory_conditions: Optional[Dict[str, Any]] = None
) -> Tuple[str, List[Any]]:
    """
    Helper to build WHERE clauses and parameters for metric/listing queries.
    Requires ngroup_id, handles optional filters and conditions.
    End date is treated as inclusive.
    """
    where_clauses = []
    params: List[Any] = []
    param_index = 1

    base_query = """
        FROM file f
        JOIN file_status fs ON f.id = fs.id
        JOIN collection c ON f.collection_id = c.id
    """
    joins = ""

    where_clauses.append(f"c.ngroup_id = ${param_index}")
    params.append(ngroup_id)
    param_index += 1

    if mandatory_conditions:
        for field, value in mandatory_conditions.items():
            if field == 'fs.status':
                 where_clauses.append(f"{field} = ${param_index}::file_status_type")
            else:
                 where_clauses.append(f"{field} = ${param_index}")
            params.append(value)
            param_index += 1

    if optional_filters.get("start_date"):
        where_clauses.append(f"fs.upload_time >= ${param_index}")
        params.append(optional_filters["start_date"])
        param_index += 1
    if optional_filters.get("end_date"):
        where_clauses.append(f"DATE(fs.upload_time) <= ${param_index}")
        params.append(optional_filters["end_date"])
        param_index += 1
    if optional_filters.get("user_id"):
        where_clauses.append(f"f.cueuser_uploaded = ${param_index}")
        params.append(optional_filters["user_id"])
        param_index += 1
    if optional_filters.get("collection_id"):
        where_clauses.append(f"f.collection_id = ${param_index}")
        params.append(optional_filters["collection_id"])
        param_index += 1
    if optional_filters.get("provider_id"):
        where_clauses.append(f"c.provider_id = ${param_index}")
        params.append(optional_filters["provider_id"])
        param_index += 1

    query_suffix = base_query + joins
    if where_clauses:
        query_suffix += " WHERE " + " AND ".join(where_clauses)

    return query_suffix, params

async def create_file_status_in_db(conn: Connection, params: Tuple) -> List:
    """Inserts a new file_status record into the database."""
    insert_query = """
        INSERT INTO file_status (id, status, scan_results, upload_time, scan_start, scan_end)
        VALUES ($1, $2::file_status_type, $3::jsonb, $4, $5, $6)
        RETURNING id, upload_time, scan_start, scan_end, egress_start, status, scan_results
    """
   
    try:
        return await conn.fetch(insert_query, *params)
    except UniqueViolationError as e:
        logger.error(f"Failed to create file_status due to unique constraint violation: {e}", exc_info=True)
        raise ValueError("A file_status record with the given ID already exists.")
    except ForeignKeyViolationError as e:
        logger.error(f"Failed to create file_status due to foreign key violation: {e}", exc_info=True)
        raise ValueError(f"Invalid file id provided: {params[0]}") from e
    except DataError as e:
        logger.error(f"Failed to create file_status due to invalid data: {e}", exc_info=True)
        raise ValueError("Invalid data provided for creating a file_status record.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating a file_status record: {e}", exc_info=True)
        raise

async def get_file_status_from_db(conn: Connection, params: Tuple) -> List:
    """Retrieves a file_status record from the database by its id."""
    select_query = """
        SELECT id, upload_time, scan_start, scan_end, egress_start, status, scan_results::text
        FROM file_status
        WHERE id = $1
    """
    try:
        return await conn.fetch(select_query, *params)
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting a file_status record: {e}", exc_info=True)
        raise

async def update_file_status_in_db(conn: Connection, params: Tuple) -> List:
    """Updates an existing file_status record in the database."""
    
    update_fields, id = params
    set_clause_parts = []
    values = []
    param_idx = 1

    for field, value in update_fields.items():
        if field == "scan_results":
            set_clause_parts.append(f"{field} = ${param_idx}::jsonb")
        elif field == "status":
            set_clause_parts.append(f"{field} = ${param_idx}::file_status_type")
        else: 
            set_clause_parts.append(f"{field} = ${param_idx}")
        values.append(value)
        param_idx += 1

    values.append(id)
    set_clause = ", ".join(set_clause_parts)

    update_query = f"""
        UPDATE file_status
        SET {set_clause}
        WHERE id = ${param_idx}
        RETURNING id, upload_time, scan_start, scan_end, egress_start, status, scan_results::text
    """
    try:
        return await conn.fetch(update_query, *values)
    except ForeignKeyViolationError as e: # Should not happen on update if ID exists
        logger.error(f"Failed to update file status due to foreign key violation: {e}",exc_info=True)
        raise ValueError("Invalid id provided during update.") from e
    except DataError as e:
        logger.error(f"Failed to update file_status: invalid data: {e}", exc_info=True)
        raise ValueError(f"Invalid data provided for updating file_status: {e}") from e
    except Exception as e:
        logger.error(f"Error updating file_status: {e}", exc_info=True)
        raise

async def delete_file_status_from_db(conn: Connection, params: Tuple) -> bool:
    """Deletes a file_status record from the database by id."""
    
    delete_query = """
        DELETE FROM file_status
        WHERE id = $1
    """
    try:
        result = await conn.execute(delete_query, *params)
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting a file_status record: {e}", exc_info=True)
        raise

async def list_file_statuses_from_db(conn: Connection, ngroup_id: UUID) -> List:
    """Retrieves all file_status records for a specific ngroup."""
    select_query = """
        SELECT fs.id, fs.upload_time, fs.scan_start, fs.scan_end, fs.egress_start, fs.status, fs.scan_results::text
        FROM file_status fs
        JOIN file f ON fs.id = f.id
        JOIN collection c ON f.collection_id = c.id
        WHERE c.ngroup_id = $1
        ORDER BY fs.upload_time DESC -- Example order
    """
    try:
        return await conn.fetch(select_query, ngroup_id)
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing file_status records: {e}", exc_info=True)
        raise


async def get_daily_volume_from_db(conn: Connection, ngroup_id: UUID, filters: Dict[str, Any]) -> List:
    """Retrieves daily file volume sum(size_bytes) for a specific ngroup."""
    query_suffix, params = await _build_metrics_query_parts(ngroup_id, filters)
    select_clause = "SELECT DATE(fs.upload_time) AS day, SUM(f.size_bytes) AS value "
    group_by_clause = " GROUP BY day ORDER BY day"
    full_query = select_clause + query_suffix + group_by_clause
    logger.debug(f"Executing daily volume query: {full_query} with params: {params}")
    try:
        return await conn.fetch(full_query, *params)
    except Exception as e:
        logger.error(f"Error fetching daily volume: {e}", exc_info=True)
        raise

async def get_daily_count_from_db(conn: Connection, ngroup_id: UUID, filters: Dict[str, Any]) -> List:
    """Retrieves daily file count for a specific ngroup."""
    query_suffix, params = await _build_metrics_query_parts(ngroup_id, filters)
    select_clause = "SELECT DATE(fs.upload_time) AS day, COUNT(f.id) AS value "
    group_by_clause = " GROUP BY day ORDER BY day"
    full_query = select_clause + query_suffix + group_by_clause
    logger.debug(f"Executing daily count query: {full_query} with params: {params}")
    try:
        return await conn.fetch(full_query, *params)
    except Exception as e:
        logger.error(f"Error fetching daily count: {e}", exc_info=True)
        raise

async def get_overall_volume_from_db(conn: Connection, ngroup_id: UUID, filters: Dict[str, Any]) -> Optional[int]:
    """Retrieves overall file volume sum(size_bytes) for a specific ngroup."""
    query_suffix, params = await _build_metrics_query_parts(ngroup_id, filters)
    select_clause = "SELECT SUM(f.size_bytes) AS value "
    full_query = select_clause + query_suffix
    logger.debug(f"Executing overall volume query: {full_query} with params: {params}")
    try:
        result = await conn.fetchval(full_query, *params)
        return int(result) if result is not None else 0
    except Exception as e:
        logger.error(f"Error fetching overall volume: {e}", exc_info=True)
        raise

async def get_overall_count_from_db(conn: Connection, ngroup_id: UUID, filters: Dict[str, Any]) -> Optional[int]:
    """Retrieves overall file count for a specific ngroup."""
    query_suffix, params = await _build_metrics_query_parts(ngroup_id, filters)
    select_clause = "SELECT COUNT(f.id) AS value "
    full_query = select_clause + query_suffix
    logger.debug(f"Executing overall count query: {full_query} with params: {params}")
    try:
        result = await conn.fetchval(full_query, *params)
        return int(result) if result is not None else 0
    except Exception as e:
        logger.error(f"Error fetching overall count: {e}", exc_info=True)
        raise

async def get_status_counts_from_db(conn: Connection, ngroup_id: UUID, filters: Dict[str, Any]) -> List:
    """Retrieves counts for each file status for a specific ngroup."""
    query_suffix, params = await _build_metrics_query_parts(ngroup_id, filters)
    select_clause = "SELECT fs.status::text, COUNT(f.id) AS count "
    group_by_clause = " GROUP BY fs.status"
    full_query = select_clause + query_suffix + group_by_clause
    logger.debug(f"Executing status counts query: {full_query} with params: {params}")
    try:
        return await conn.fetch(full_query, *params)
    except Exception as e:
        logger.error(f"Error fetching status counts: {e}", exc_info=True)
        raise

async def _build_list_select_clause(status: str) -> str:
    """Helper to build select clauses for list_files_by_status_from_db."""
    base_clause = "SELECT f.id, f.name, f.type, f.cueuser_uploaded, f.size_bytes, f.collection_id, f.edpub, f.checksum"
    select_clause = ""

    if status == "unscanned":
        select_clause = base_clause + ", fs.upload_time"
    elif status == "clean":
        select_clause = base_clause + ", fs.scan_start, fs.scan_end"
    elif status == "infected" or status == "scan_failed":
        select_clause = base_clause + ", fs.scan_results::text"
    elif status == "distributed":
        select_clause = base_clause + ", fs.egress_start"
    else:
        select_clause = base_clause

    return select_clause


async def list_files_by_status_from_db(conn: Connection, ngroup_id: UUID, status: str, filters: Dict[str, Any], limit: int, offset: int) -> List:
    """Retrieves a paginated list of files for a specific ngroup matching a status."""
    mandatory = {'fs.status': status}
    query_suffix, params = await _build_metrics_query_parts(ngroup_id, filters, mandatory_conditions=mandatory)
    limit_param_index = len(params) + 1
    offset_param_index = len(params) + 2
    params.extend([limit, offset])
    select_clause = await _build_list_select_clause(status)
    order_by_clause = " ORDER BY fs.upload_time DESC "
    pagination_clause = f" LIMIT ${limit_param_index} OFFSET ${offset_param_index}"
    full_query = select_clause + query_suffix + order_by_clause + pagination_clause
    logger.debug(f"Executing list files by status query: {full_query} with params: {params}")
    try:
        return await conn.fetch(full_query, *params)
    except Exception as e:
        logger.error(f"Error listing files by status: {e}", exc_info=True)
        raise

async def count_files_by_status_from_db(conn: Connection, ngroup_id: UUID, status: str, filters: Dict[str, Any]) -> int:
    """Counts total files for a specific ngroup matching a status."""
    mandatory = {'fs.status': status}
    query_suffix, params = await _build_metrics_query_parts(ngroup_id, filters, mandatory_conditions=mandatory)
    select_clause = "SELECT COUNT(f.id) "
    full_query = select_clause + query_suffix
    logger.debug(f"Executing count files by status query: {full_query} with params: {params}")
    try:
        count = await conn.fetchval(full_query, *params)
        return int(count) if count is not None else 0
    except Exception as e:
        logger.error(f"Error counting files by status: {e}", exc_info=True)
        raise