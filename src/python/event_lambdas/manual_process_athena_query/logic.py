import os
import structlog
import boto3
from botocore.exceptions import ClientError
import json
from model import AthenaQueryDetails
from pydantic import ValidationError

logger = structlog.get_logger(__name__)
lambda_client = boto3.client("lambda")
athena_client = boto3.client("athena")

class ManualProcessAthenaQueryError(Exception):
    pass

async def validate_athena_query_details(athena_query_details: AthenaQueryDetails):
    try:
        athena_details = AthenaQueryDetails(**athena_query_details)
    except ValidationError as e:
        logger.error("athena_details.invalid", error=e)
        raise ManualProcessAthenaQueryError(str(e))

    # The query result must be accessible in the results bucket to processed into JSON
    if not await check_result_exists(athena_details.query_id):
        raise ManualProcessAthenaQueryError(f"No Athena results for {athena_details.query_id}")

    return athena_details

async def check_result_exists(query_id: str): 
    try:
        # Attempt to check query executions
        response = athena_client.get_query_execution(QueryExecutionId=query_id)
        logger.info("athena",response=response)
        return True  
    except ClientError as e:
        logger.error("query_execution.expired_or_does_not_exists", exc_info=True)
        raise ManualProcessAthenaQueryError("Cannot process query") 


async def invoke_process_athena_query(current_state: str, query_id: str ):
    """Prepares payload and invokes the process_athena_query Lambda."""

    payload = {"detail":{"currentState": current_state, "queryExecutionId": query_id}}
    try:
        logger.info("process_athena_query.invoke.started", payload=payload)
        lambda_client.invoke(
            FunctionName=os.environ['PROCESS_ATHENA_QUERY_ARN'],
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
        logger.info("process_athena_query.invoke.completed")
    except Exception: 
        logger.error("process_athena_query.invoke.failed", exc_info=True)
        raise ManualProcessAthenaQueryError("Failed to invoke process_athena_query")

    
    