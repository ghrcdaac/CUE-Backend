import os
import boto3
from botocore.exceptions import ClientError
import csv
import json
from io import StringIO
import structlog

logger = structlog.get_logger(__name__)

# Initialize clients once per container for reuse
athena_client = boto3.client('athena', region_name=os.environ.get('AWS_REGION'))
s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION'))
RESULTS_BUCKET = os.environ["RESULTS_BUCKET"]

class QueryProcessingError(Exception):
    pass

async def get_query_results_as_json(query_exec_id: str) -> str:
    """Gets the Athena query results CSV, converts it to JSON, and returns the JSON string."""
    try:
        response = athena_client.get_query_execution(QueryExecutionId=query_exec_id)
        result_location = response['QueryExecution']['ResultConfiguration']['OutputLocation']

        bucket = result_location.split('/')[2]
        key = '/'.join(result_location.split('/')[3:])
        
        logger.info("athena.results.fetching", bucket=bucket, key=key)
        s3_response = s3_client.get_object(Bucket=bucket, Key=key)
        csv_content = s3_response['Body'].read().decode('utf-8')
        result = await parse_csv_to_json(csv_content)
        return json.dumps(result)
    except ClientError as e:
        logger.error("aws.client_error.get_results", exc_info=True)
        raise QueryProcessingError(f"AWS Error getting results for {query_exec_id}: {e.response['Error']['Message']}")
    except Exception as e:
        logger.error("athena.results.unexpected_error", exc_info=True)
        raise QueryProcessingError(f"Unexpected error getting results for {query_exec_id}: {e}")

async def parse_csv_to_json(csv_content: str):
    csv_reader = csv.DictReader(StringIO(csv_content))
    results = []
    for row in csv_reader:
        processed_row = {}
        for column, value in row.items():
            if value is None or value.strip() == "":
                # Handle empty or null values
                processed_row[column] = None
            else:
                try:
                    # Attempt to convert str to actual type
                    processed_row[column] = json.loads(value)
                except json.JSONDecodeError as e:
                    # Could not convert str leave as str 
                    processed_row[column] = value
        results.append(processed_row) 
    return results

async def get_query_error_reason(query_exec_id: str) -> str:
    """Gets the failure reason for a FAILED Athena query."""
    try:
        response = athena_client.get_query_execution(QueryExecutionId=query_exec_id)
        return response['QueryExecution']['Status'].get('StateChangeReason', 'No reason provided.')
    except ClientError as e:
        logger.error("aws.client_error.get_error_reason", exc_info=True)
        return "Failed to retrieve error reason due to an AWS error."

async def store_result_in_s3(result_json: str, key: str):
    """Stores the final JSON result string in the dedicated results bucket."""
    try:
        s3_client.put_object(Body=result_json, Bucket=RESULTS_BUCKET, Key=key, ContentType="application/json")
        logger.info("s3.result.stored", bucket=RESULTS_BUCKET, key=key)
    except ClientError as e:
        logger.error("aws.client_error.store_result", exc_info=True)
        raise QueryProcessingError(f"Failed to store result in S3: {e.response['Error']['Message']}")
