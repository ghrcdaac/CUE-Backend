from typing import List, Dict 
from datetime import datetime
import os
import boto3
import asyncpg
from db import get_files_sizes, update_file_status_with_cost
from model import FileSize, FileCost
import structlog

from core.db_pool import get_database_pool

logger = structlog.get_logger(__name__)
CSS_ROLE_ARN = str(os.getenv("CSS_ROLE_ARN", ""))


async def get_css_creds():
    sts_client = boto3.client('sts')
    assumed_role_object = sts_client.assume_role(RoleArn=CSS_ROLE_ARN, RoleSessionName="CostExplorerSession")
    credentials = assumed_role_object['Credentials']
    return credentials
    

async def get_scan_cost(start_date: datetime, end_date: datetime) -> Dict[str,float]:
    """Use cost explorer boto3 client to get the cost metrics from the css account"""
    css_creds = await get_css_creds()
    cost_explore_client = boto3.client("ce",
        aws_access_key_id=css_creds["AccessKeyId"],
        aws_secret_access_key=css_creds["SecretAccessKey"],
        aws_session_token=css_creds["SessionToken"]
    )
    response = cost_explore_client.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.strftime("%Y-%m-%d"),
            "End": end_date.strftime("%Y-%m-%d")
        },
        Granularity="DAILY",
        Metrics=["UnblendedCost", "NetUnblendedCost", "NetAmortizedCost"],
        Filter={
            "Tags":{
                "Key":"Application",
                "Values":[
                    "CSS"
                ],
                "MatchOptions":["EQUALS"]
            }
        }
    )
    cost = response["ResultsByTime"][0]["Total"]
    try:
        cost = {
            "UnblendedCost": float(cost["UnblendedCost"]["Amount"]),
            "NetUnblendedCost": float(cost["NetUnblendedCost"]["Amount"]),
            "NetAmortizedCost": float(cost["NetAmortizedCost"]["Amount"])
        }
        return cost
    except Exception as e:
        logger.error("Error could not get yesterday's cost.")
        raise e

async def get_aws_cost(start_date: datetime, end_date: datetime) -> Dict[str,float]:
    """Use cost explorer boto3 client to get the cost metric(s) and return back the cost metrics back as smaller dictionary"""
    cost_explore_client = boto3.client("ce")
    response = cost_explore_client.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.strftime("%Y-%m-%d"),
            "End": end_date.strftime("%Y-%m-%d")
        },
        Granularity="DAILY",
        Metrics=["UnblendedCost", "NetUnblendedCost", "NetAmortizedCost"],
    )
    cost = response["ResultsByTime"][0]["Total"]
    try:
        cost = {
            "UnblendedCost": float(cost["UnblendedCost"]["Amount"]),
            "NetUnblendedCost": float(cost["NetUnblendedCost"]["Amount"]),
            "NetAmortizedCost": float(cost["NetAmortizedCost"]["Amount"])
        }
        return cost
    except Exception as e:
        logger.error("Error could not get yesterday's cost.")
        raise e

async def calculate_cost_per_file(files: List[FileSize], type:str, cost_per_byte: Dict[str, float]) -> List[FileCost]:
    """Calculate the per file cost for each cost metric"""
    file_costs = []
    for file in files:
        size_bytes = file.size_bytes
        fc = FileCost(id=file.id,
                      type=type,
                      unblended_cost=size_bytes * cost_per_byte["UnblendedCost"],
                      net_unblended_cost=size_bytes * cost_per_byte["NetUnblendedCost"],
                      net_amortized_cost=size_bytes * cost_per_byte["NetAmortizedCost"])
        file_costs.append(fc)
    return file_costs

async def update_file_costs(start_date: datetime, end_date: datetime, pool:asyncpg.Pool):
    try:
        pool = await get_database_pool()
        if not pool:
            logger.critical("db.pool.not_available.failing_invocation")

        async with pool.acquire() as conn:
            # get files and total upload volume of the previous day
            db_rows = await get_files_sizes(conn, (start_date, end_date))

        files = [FileSize.from_db_row(db_row) for db_row in db_rows]
        if not files:
            logger.info("No files to update")
            return
        total_size = 0
        for file in files:
            total_size += file.size_bytes
        logger.info(f"Yesterday's total size_bytes {total_size}")
        # get the cost
        scan_cost = await get_scan_cost(start_date, end_date)
        aws_cost = await get_scan_cost(start_date, end_date)
        logger.info(scan_cost)
        logger.info(aws_cost)

        # calculate the cost per byte
        scan_cost_per_byte = {
            "UnblendedCost": scan_cost["UnblendedCost"] / total_size if scan_cost["UnblendedCost"] > 0.0 else 0.0,
            "NetUnblendedCost": scan_cost["NetUnblendedCost"] / total_size if scan_cost["NetUnblendedCost"] > 0.0 else 0.0,
            "NetAmortizedCost": scan_cost["NetAmortizedCost"] /total_size if scan_cost["NetAmortizedCost"] > 0.0 else 0.0,
        }

        aws_cost_per_byte = {
            "UnblendedCost": aws_cost["UnblendedCost"] / total_size if aws_cost["UnblendedCost"] > 0.0 else 0.0,
            "NetUnblendedCost": aws_cost["NetUnblendedCost"] / total_size if aws_cost["NetUnblendedCost"] > 0.0 else 0.0,
            "NetAmortizedCost": aws_cost["NetAmortizedCost"] /total_size if aws_cost["NetAmortizedCost"] > 0.0 else 0.0,
        }

        # calculate cost per file
        scan_file_costs = await calculate_cost_per_file(files, "scan", scan_cost_per_byte)
        aws_file_costs = await calculate_cost_per_file(files, "aws", aws_cost_per_byte)

        async with pool.acquire() as conn: 
            for file_cost in scan_file_costs:
                params = (file_cost.id, file_cost.model_dump_json(include={'type','unblended_cost', 'net_unblended_cost', 'net_amortized_cost'}))
                await update_file_status_with_cost(conn, params)
            for file_cost in aws_file_costs:
                params = (file_cost.id, file_cost.model_dump_json(include={'type','unblended_cost', 'net_unblended_cost', 'net_amortized_cost'}))
                await update_file_status_with_cost(conn, params)
    except Exception as e:
        logger.error("Failed to update cost", exc_info=True)
        raise e
