import os
import json
from uuid import UUID
from datetime import datetime
from typing import List
from fastapi import HTTPException
import boto3
from botocore.exceptions import ClientError
from lambda_utils.type_util.file_status import MetricsQueryParameters
from lambda_utils.type_util.archive import ArchiveReturn
import lambda_utils.database_util.archive as archive_db
import logging

logger = logging.getLogger(__name__)

DB_NAME = os.environ["ARCHIVE_DB"]
ARCHIVE_BUCKET = os.environ["ARCHIVE_BUCKET"]

async def start_archive_query(ngroup_id: UUID, filters:MetricsQueryParameters) -> UUID:
    filter_dict = filters.model_dump(exclude=None)

    # Build the query to execute
    query = await archive_db.query_archive_database(ngroup_id, filter_dict)
    logger.info(query)
    now = datetime.now()

    year = now.year
    month = now.month
    day = now.day
    try:
        athena_client = boto3.client('athena', region_name=os.environ.get('AWS_REGION'))
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={ "Database": DB_NAME }, ResultConfiguration={
                "OutputLocation": f"s3://{ARCHIVE_BUCKET}/results/{ngroup_id}/{year}/{month}/{day}"
            }
        )
        query_exc_id = response.get("QueryExecutionId")
        return query_exc_id
    except ClientError as ce:
        logger.error(f"Athena ClientError start_query_execution: {ce}", exc_info=True)
        if ce.response["Error"]["Code"] == "InvalidRequestExecution":
            raise HTTPException(status_code=400, detail="Invalid start query request.") from ce
        if ce.response["Error"]["Code"] == "InternalServerException":
            raise HTTPException(status_code=500, detail="Error starting query." )
        if ce.response["Error"]["Code"] == "TooManyRequestsException":
            raise HTTPException(status_code=429, detail="Too many request.Please try again later.")
        raise ce
    except Exception as e:
        logger.error(f"Error starting athena query {e}", exc_info=True)
        raise e

async def get_query_status(query_exec_id: str) -> str:
    try:
        athena_client = boto3.client('athena', region_name=os.environ.get('AWS_REGION'))
        response = athena_client.get_query_execution(
            QueryExecutionId=query_exec_id
        )
        query_status = response['QueryExecution']['Status']['State']
        return query_status
    except ClientError as ce:
        logger.error(f"Athena ClientError get_query_execution: {ce}", exc_info=True)
        if ce.response["Error"]["Code"] == "InvalidRequestExecution":
            raise HTTPException(status_code=400, detail="Invalid get query status request") from ce
        if ce.response["Error"]["Code"] == "InternalServerException":
            raise HTTPException(status_code=500, detail="Error getting query status.")
        raise ce
    except Exception as e:
        logger.error(f"Error retrieving query status: {e}", exc_info=True)
        raise e

async def get_query_results(query_exec_id: UUID) -> List[ArchiveReturn]:
    s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION'))
    bucket_name = os.environ.get("ARCHIVE_RESULTS_BUCKET")
    key = f'{query_exec_id}.json'
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        json_data = response["Body"].read().decode('utf-8')
        json_array = json.loads(json_data)
        if not isinstance(json_array, list):
            logger.error(f"Query failed for this reason {json_array["message"]}")
            raise HTTPException(status_code=400, detail=json_array["detail"])
        results = [ArchiveReturn.convert_str(json_obj) for json_obj in json_array]
        return results
    except ClientError as ce:
        logger.error(f"S3 ClientError get_object {ce}", exc_info=True)
        if ce.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(status_code=400, detail="No result exists for query_execution_id") from ce
        raise ce
    except Exception as e:
        logger.error(f"Error retrieving results {e}", exc_info=True)
        raise e
