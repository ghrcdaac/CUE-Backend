import json
from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import file_status as file_status_db
from lambda_utils.database_util import file as file_db
from lambda_utils.type_util.file_status import (FileStatusCreate, FileStatusReturn,
                                              FileStatusUpdate, DailyMetricItem,
                                              OverallMetricResult, MetricsQueryParameters,
                                              UnscannedFileReturn, CleanFileReturn,
                                              InfectedFileReturn, ScanFailedFileReturn,
                                              DistributedFileReturn, FileResponse,
                                              FileStatusMetricsSummary)

from lambda_utils.type_util.file import FileReturn

from typing import List, Tuple, Dict
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class FileStatusNotFoundError(Exception):
     def __init__(self, id: UUID):
         super().__init__(f"File status not found for file ID: {id}")
         self.id = id

class AuthorizationError(Exception):
    def __init__(self, message="User not authorized for this operation or resource."):
        super().__init__(message)


BYTES_TO_GB = 1 / (1024**3)
VALID_FILE_STATUSES = ["unscanned", "clean", "infected", "scan_failed", "distributed"]



async def create_file_status(file_status: FileStatusCreate, user_ngroup_id: UUID) -> FileStatusReturn:
    """Creates a new file_status record, verifying file belongs to user's ngroup."""
    pool: Pool = await get_connection_pool()
    conn = None
    # Verify the referenced file exists and belongs to the user's ngroup
    try:
        # Use async with to ensure connection release
        async with pool.acquire() as conn:
            file_ngroup_id = await file_db.get_ngroup_id_for_file_db(conn, file_status.id)
            if not file_ngroup_id:
                raise FileStatusNotFoundError(id=file_status.id)
            if file_ngroup_id != user_ngroup_id:
                raise AuthorizationError(f"File {file_status.id} does not belong to user's group {user_ngroup_id}.")

            scan_results_json = json.dumps(file_status.scan_results) if file_status.scan_results else None
            params = (
                file_status.id,
                file_status.status,
                scan_results_json,
                file_status.upload_time,  
                file_status.scan_start,   
                file_status.scan_end      
            )
            # Pass the acquired connection to the db function
            result = await file_status_db.create_file_status_in_db(conn, params)

        if not result:
            raise Exception("Failed to create file_status record after verification.")
        return FileStatusReturn.from_db_row(result[0])

    except (AuthorizationError, FileStatusNotFoundError, ValueError):
        raise
    except Exception as e:
        logger.error(f"Error creating file_status for file {file_status.id}: {e}", exc_info=True)
        raise
   


async def get_file_status(id: UUID) -> FileStatusReturn:
    """Retrieves a file_status record by id. Authorization check happens in endpoint."""
    pool: Pool = await get_connection_pool()
    params = (id,)
    try:
        # Using query helper which handles connection correctly
        result = await query(pool, file_status_db.get_file_status_from_db, params, row_mapper=FileStatusReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise FileStatusNotFoundError(id=id)
    except FileStatusNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting file_status {id}: {e}", exc_info=True)
        raise
    

async def update_file_status(id: UUID, file_status_update: FileStatusUpdate) -> FileStatusReturn:
    """Updates an existing file_status record. Authorization check happens in endpoint."""
    pool: Pool = await get_connection_pool()
    update_fields = {k: v for k, v in file_status_update.model_dump(exclude_none=True).items()}
    if not update_fields:
         try:
            return await get_file_status(id) # Return current if no update
         except FileStatusNotFoundError:
             raise # Propagate if not found

    params = (update_fields, id)
    try:
         # Using query helper which handles connection correctly
        result = await query(pool, file_status_db.update_file_status_in_db, params, row_mapper=FileStatusReturn.from_db_row)
        if result:
            return result[0]
        else:
            raise FileStatusNotFoundError(id=id)
    except (FileStatusNotFoundError, ValueError):
        raise
    except Exception as e:
        logger.error(f"Error updating file_status {id}: {e}", exc_info=True)
        raise
    

async def delete_file_status(id: UUID) -> bool:
    """Deletes a file_status record by id. Authorization check happens in endpoint."""
    pool: Pool = await get_connection_pool()
    params = (id,)
    try:

        async with pool.acquire() as conn:
             result = await file_status_db.delete_file_status_from_db(conn, params)

        if not result:
            # If deletion affected 0 rows, it means the ID wasn't found
            raise FileStatusNotFoundError(id=id)
        return result
    except FileStatusNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error deleting file_status {id}: {e}", exc_info=True)
        raise
   

async def list_file_statuses(ngroup_id: UUID) -> List[FileStatusReturn]:
    """Retrieves all file_status records for a specific ngroup."""
    pool: Pool = await get_connection_pool()
    try:
        # Using query helper which handles connection correctly
        results = await query(pool, file_status_db.list_file_statuses_from_db, *(ngroup_id,), row_mapper=FileStatusReturn.from_db_row)
        return results
    except Exception as e:
        logger.error(f"Error listing file_statuses for ngroup {ngroup_id}: {e}", exc_info=True)
        raise
    

async def get_file_status_counts(ngroup_id: UUID, filters: MetricsQueryParameters) -> Dict[str, int]:
    """Calculates counts for each file status for a specific ngroup."""
    pool: Pool = await get_connection_pool()
    filter_dict = filters.model_dump(exclude_none=True)
    status_counts = {status: 0 for status in VALID_FILE_STATUSES}
    try:
        # Use async with to ensure connection release
        async with pool.acquire() as conn:
            results = await file_status_db.get_status_counts_from_db(conn, ngroup_id, filter_dict)
        for row in results:
            status_counts[row['status']] = row['count']
        return status_counts
    except Exception as e:
        logger.error(f"Error calculating status counts: {e}", exc_info=True)
        raise
   

async def calculate_daily_volume(ngroup_id: UUID, filters: MetricsQueryParameters) -> List[DailyMetricItem]:
    """Calculates daily volume in GB for a specific ngroup."""
    pool: Pool = await get_connection_pool()
    filter_dict = filters.model_dump(exclude_none=True)
    try:
        # Use async with to ensure connection release
        async with pool.acquire() as conn:
            results = await file_status_db.get_daily_volume_from_db(conn, ngroup_id, filter_dict)
        return [DailyMetricItem(day=row['day'], value=float(row['value']) * BYTES_TO_GB) for row in results]
    except Exception as e:
        logger.error(f"Error calculating daily volume: {e}", exc_info=True)
        raise
   

async def calculate_daily_count(ngroup_id: UUID, filters: MetricsQueryParameters) -> List[DailyMetricItem]:
    """Calculates daily file count for a specific ngroup."""
    pool: Pool = await get_connection_pool()
    filter_dict = filters.model_dump(exclude_none=True)
    try:
        # Use async with to ensure connection release
        async with pool.acquire() as conn:
            results = await file_status_db.get_daily_count_from_db(conn, ngroup_id, filter_dict)
        return [DailyMetricItem(day=row['day'], value=float(row['value'])) for row in results]
    except Exception as e:
        logger.error(f"Error calculating daily count: {e}", exc_info=True)
        raise
   

async def calculate_overall_volume(ngroup_id: UUID, filters: MetricsQueryParameters) -> OverallMetricResult:
    """Calculates overall volume in GB for a specific ngroup."""
    pool: Pool = await get_connection_pool()
    filter_dict = filters.model_dump(exclude_none=True)
    try:
        # Use async with to ensure connection release
        async with pool.acquire() as conn:
            total_bytes = await file_status_db.get_overall_volume_from_db(conn, ngroup_id, filter_dict)
        total_gb = float((total_bytes or 0) * BYTES_TO_GB)
        return OverallMetricResult(
            value=total_gb,
            start_date=filters.start_date,
            end_date=filters.end_date
        )
    except Exception as e:
        logger.error(f"Error calculating overall volume: {e}", exc_info=True)
        raise
   

async def calculate_overall_count(ngroup_id: UUID, filters: MetricsQueryParameters) -> OverallMetricResult:
    """Calculates overall file count for a specific ngroup."""
    pool: Pool = await get_connection_pool()
    filter_dict = filters.model_dump(exclude_none=True)
    try:
        # Use async with to ensure connection release
        async with pool.acquire() as conn:
            total_count = await file_status_db.get_overall_count_from_db(conn, ngroup_id, filter_dict)
        return OverallMetricResult(
            value=float(total_count or 0),
            start_date=filters.start_date,
            end_date=filters.end_date
            )
    except Exception as e:
        logger.error(f"Error calculating overall count: {e}", exc_info=True)
        raise
   

async def list_files_by_status(
    ngroup_id: UUID,
    status: str,
    filters: MetricsQueryParameters,
    page: int,
    page_size: int
) -> Tuple[List[FileResponse], int]:
    """Lists files for a specific ngroup matching a status with filters and pagination."""
    if status not in VALID_FILE_STATUSES:
        raise ValueError(f"Invalid status provided: {status}")

    pool: Pool = await get_connection_pool()
    filter_dict = filters.model_dump(exclude_none=True)
    offset = (page - 1) * page_size
    try:
        # Use async with to ensure connection release
        async with pool.acquire() as conn:
            # Perform both count and list within the same connection context
            total_count = await file_status_db.count_files_by_status_from_db(conn, ngroup_id, status, filter_dict)
            items = []
            if total_count > 0 and offset < total_count:
                 db_rows = await file_status_db.list_files_by_status_from_db(conn, ngroup_id, status, filter_dict, page_size, offset)
                 # Assuming FileReturn has a from_db_row method
                 if status == "unscanned":
                     items = [UnscannedFileReturn.from_db_row(row) for row in db_rows]
                 elif status == "clean":
                     items = [CleanFileReturn.from_db_row(row) for row in db_rows]
                 elif status == "infected":
                     items = [InfectedFileReturn.from_db_row(row) for row in db_rows]
                 elif status == "scan_failed":
                     items = [ScanFailedFileReturn.from_db_row(row) for row in db_rows]
                 elif status == "distributed":
                     items = [DistributedFileReturn.from_db_row(row) for row in db_rows]
                 else:
                    items = [FileReturn.from_db_row(row) for row in db_rows]

        return items, total_count
    except Exception as e:
        logger.error(f"Error listing files by status: {e}", exc_info=True)
        raise

async def get_metrics_summary(ngroup_id: UUID, filters: MetricsQueryParameters) -> FileStatusMetricsSummary:
    """Calculates and aggregates all file status metrics."""
    pool: Pool = await get_connection_pool()
    filter_dict = filters.model_dump(exclude_none=True)

    try:
        async with pool.acquire() as conn:
            # Fetch all data using the single connection
            daily_volume_rows = await file_status_db.get_daily_volume_from_db(conn, ngroup_id, filter_dict)
            daily_count_rows = await file_status_db.get_daily_count_from_db(conn, ngroup_id, filter_dict)
            overall_volume_bytes = await file_status_db.get_overall_volume_from_db(conn, ngroup_id, filter_dict)
            overall_count_val = await file_status_db.get_overall_count_from_db(conn, ngroup_id, filter_dict)
            status_count_rows = await file_status_db.get_status_counts_from_db(conn, ngroup_id, filter_dict)

        # Process the results
        daily_volume_result = [DailyMetricItem(day=row['day'], value=float(row['value']) * BYTES_TO_GB) for row in daily_volume_rows]
        daily_count_result = [DailyMetricItem(day=row['day'], value=float(row['value'])) for row in daily_count_rows]

        overall_volume_result = OverallMetricResult(
            value=float((overall_volume_bytes or 0) * BYTES_TO_GB),
            start_date=filters.start_date,
            end_date=filters.end_date
        )
        overall_count_result = OverallMetricResult(
            value=float(overall_count_val or 0),
            start_date=filters.start_date,
            end_date=filters.end_date
        )

        status_counts_result = {status: 0 for status in VALID_FILE_STATUSES}
        for row in status_count_rows:
             if row['status'] in status_counts_result: # Ensure status from DB is valid
                status_counts_result[row['status']] = row['count']

        # Assemble the final summary object
        summary = FileStatusMetricsSummary(
            daily_volume=daily_volume_result,
            daily_count=daily_count_result,
            overall_volume=overall_volume_result,
            overall_count=overall_count_result,
            status_counts=status_counts_result
            # Optionally include filter params here if needed in response
        )
        return summary

    except Exception as e:
        logger.error(f"Error calculating metrics summary for ngroup {ngroup_id}: {e}", exc_info=True)
        raise