import boto3
from botocore.exceptions import ClientError
import csv
import json
import logging
import os 
from io import StringIO
from typing import Dict

logger = logging.getLogger(__name__)
logger.setLevel("INFO")

def handler(event: Dict, context):
    """Process the results for succeeded athena queries into a JSON file and stores it into a dedicated S3 bucket"""
    try:
        detail = event.get('detail')
        if not detail:
            logger.info("Event is missing detail cannot process further.")
            return
        results_bucket = os.environ["RESULTS_BUCKET"]
        query_state = detail.get("currentState")
        query_exec_id = detail.get("queryExecutionId")
        key = f"{query_exec_id}.json"
        if query_state == "SUCCEEDED":
            results_json = get_results(query_exec_id)
            store_result(results_json, results_bucket, key)
            logger.info(f"Successfully stored {key}")

        if query_state == "FAILED":
            logger.info(f"query_execution_id {query_exec_id} failed")
            error_reason_msg = get_error_reason(query_exec_id)
            results_json = json.dumps({"detail":"Failed", "message":error_reason_msg})
            store_result(results_json,results_bucket, key)

    except KeyError as ke:
        logger.error(f"Expected key is missing {ke}", exc_info=True)
    except ClientError as ce:
        message = ce.response["Error"]["Message"]
        code = ce.response["Error"]["Code"]
        logger.error(f"{code}: {message}")
    except Exception as e:
        logger.error(f"Unexpected error occurred while processing athena query results {e}", exc_info=True)
    finally:
        return

def get_results(query_exec_id: str) -> str:
    """Gets the results of the query from results bucket"""
    try:
        athena_client = boto3.client('athena')
        s3_client = boto3.client('s3')

        response = athena_client.get_query_execution(QueryExecutionId=query_exec_id)
        result_location = response['QueryExecution']['ResultConfiguration']['OutputLocation']

        # Extract bucket and key from the result_location
        bucket = result_location.split('/')[2]  # Extracting bucket name
        key = '/'.join(result_location.split('/')[3:])  # Extracting object key

        # Read the CSV file from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        csv_content = response['Body'].read().decode('utf-8')

        # Convert CSV content to JSON
        csv_reader = csv.DictReader(StringIO(csv_content),)
        json_result = json.dumps(list(csv_reader))
        return json_result
    except Exception as e:
        logging.error(f"Error processing the file: {e}")
        raise e

def get_error_reason(query_exec_id: str) -> str:
    try:
        error_msg = ""
        athena_client = boto3.client("athena")
        response = athena_client.get_query_execution(QueryExecutionId=query_exec_id)
        error_msg = response['QueryExecution']['Status']['StateChangeReason']
        return error_msg
    except KeyError as ke:
        logger.error(f"Expected key is missing {ke}", exc_info=True)
        raise
    except ClientError as ce:
        message = ce.response["Error"]["Message"]
        code = ce.response["Error"]["Code"]
        logger.error(f"{code}: {message}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error occurred while get athena query error cause {e}", exc_info=True)
        raise


def store_result(result:str, bucket: str, key: str):
    """Puts result into bucket as key"""
    try:
        s3_client = boto3.client("s3")
        s3_client.put_object(Body=result, Bucket=bucket, Key=key, ContentType="application/json")
    except Exception as e:
        logger.error(f"Failed to upload JSON results {e}", exc_info=True)
        raise