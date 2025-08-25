# File: src/python/api/v2/utils/archive.py

import os
from uuid import UUID
from typing import List, Dict
from fastapi import HTTPException, status
import boto3
from botocore.exceptions import ClientError
import structlog

from core.db import get_db_connection
from v2.database_util import archive as archive_db
from v2.type_util.archive import ArchiveQueryRequest
from v2.type_util.file import FileResponse

logger = structlog.get_logger(__name__)
ATHENA_DB_NAME = os.environ.get("ATHENA_DB_NAME")
ATHENA_OUTPUT_BUCKET = os.environ.get("ATHENA_OUTPUT_BUCKET")

class AthenaError(Exception):
    pass

def _get_athena_client():
    return boto3.client('athena', region_name=os.environ.get("AWS_REGION", "us-west-2"))

async def start_archive_query(ngroup_id: UUID, filters: ArchiveQueryRequest) -> str:
    """
    Securely starts an Athena query. First, it queries the local Postgres DB
    for relevant file IDs, then uses those IDs to build the Athena query.
    """
    if not ATHENA_DB_NAME or not ATHENA_OUTPUT_BUCKET:
        raise AthenaError("Archive service is not configured.")

    filter_dict = filters.model_dump(exclude_none=True)
    async with get_db_connection() as conn:
        file_ids = await archive_db.get_file_ids_by_filter(conn, ngroup_id, filter_dict)

    if not file_ids:
        # No need to run an expensive query if no files match
        raise ValueError("No archived records match the specified filters.")

    # Convert UUIDs to strings for the IN clause
    id_list_str = ", ".join(f"'{str(fid)}'" for fid in file_ids)
    athena_query = f"SELECT * FROM metrics WHERE id IN ({id_list_str});"

    athena_client = _get_athena_client()
    try:
        response = athena_client.start_query_execution(
            QueryString=athena_query,
            QueryExecutionContext={"Database": ATHENA_DB_NAME},
            ResultConfiguration={"OutputLocation": f"s3://{ATHENA_OUTPUT_BUCKET}/results/"}
        )
        return response["QueryExecutionId"]
    except ClientError as e:
        logger.error("athena.start_query.failed", error=str(e))
        raise AthenaError("Failed to start archive query.") from e

async def get_query_status(query_execution_id: str) -> Dict:
    """Gets the status of an Athena query."""
    athena_client = _get_athena_client()
    try:
        response = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
        q_status = response['QueryExecution']['Status']
        return {
            "status": q_status.get('State'),
            "reason": q_status.get('StateChangeReason')
        }
    except ClientError as e:
        logger.error("athena.get_status.failed", error=str(e))
        raise AthenaError("Failed to get query status.") from e

async def get_query_results(query_execution_id: str) -> List[FileResponse]:
    """Gets the results of a completed Athena query."""
    athena_client = _get_athena_client()
    try:
        response = athena_client.get_query_results(QueryExecutionId=query_execution_id)
        # Process Athena's complex response structure
        column_info = [col['Name'] for col in response['ResultSet']['ResultSetMetadata']['Columns']]
        results = []
        # Skip the header row (index 0)
        for row in response['ResultSet']['Rows'][1:]:
            row_data = {col_info[i]: item.get('VarCharValue') for i, item in enumerate(row['Data'])}
            results.append(FileResponse.model_validate(row_data))
        return results
    except ClientError as e:
        logger.error("athena.get_results.failed", error=str(e))
        raise AthenaError("Failed to get query results.") from e