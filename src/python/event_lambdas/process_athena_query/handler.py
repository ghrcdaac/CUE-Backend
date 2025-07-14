import boto3
from botocore.exceptions import ClientError
import csv
import json
import logging
import os 
from io import StringIO
from typing import Dict
from .logic import process_query


logger = logging.getLogger(__name__)

def handler(event, context):
    
    try:
        detail = event.get('detail')
        if not detail:
            logger.info("Event is missing detail cannot process further.")
            return
        results_bucket = os.environ["RESULTS_BUCKET"]
        query_state = detail.get("currentState")
        query_exec_id = detail.get("queryExecutionId")
        process_query(query_state, query_exec_id, results_bucket)

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
