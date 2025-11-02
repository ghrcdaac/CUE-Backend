import os
from uuid import UUID
from typing import List, Dict
from fastapi import HTTPException, status
import boto3
import json 
from botocore.exceptions import ClientError
import structlog

from core.db import get_db_connection
from v2.database_util import archive as archive_db
from v2.type_util.file_metrics import MetricsQueryParameters
from v2.type_util.file import FileResponse 
from v2.type_util.archive import ArchiveQueryResult

logger = structlog.get_logger(__name__)
ATHENA_DB_NAME = os.environ.get("ATHENA_DB_NAME")
ATHENA_OUTPUT_BUCKET = os.environ.get("ATHENA_OUTPUT_BUCKET")

class AthenaError(Exception):
    pass

def _get_athena_client():
    return boto3.client('athena', region_name=os.environ.get("AWS_REGION", "us-west-2"))

async def start_archive_query(ngroup_id: UUID, filters: MetricsQueryParameters) -> str:
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
            QueryExecutionContext={"Database": f"{ATHENA_DB_NAME}"},
            ResultConfiguration={"OutputLocation": f"s3://{ATHENA_OUTPUT_BUCKET}/results/"},
            ResultReuseConfiguration= {"ResultReuseByAgeConfiguration":{"Enabled":False}}
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
    try:
        s3_client = boto3.client('s3', region_name=os.environ.get("AWS_REGION", "us-west-2"))
        response = s3_client.get_object(Bucket=ATHENA_OUTPUT_BUCKET, Key=f"{query_execution_id}.json")
        json_data = response["Body"].read().decode('utf-8')
        result = json.loads(json_data)
        return result
    except ClientError as e:
        logger.error("athena.get_results.failed", error=str(e))
        raise AthenaError("Failed to get query results.") from e
