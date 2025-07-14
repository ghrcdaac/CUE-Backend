from typing import List, Dict, Tuple
from datetime import datetime
import os
import boto3
from .db import get_files_sizes, update_file_status_with_cost
from .model import FileSize, FileCost
from lambda_utils.database_util.db_util import get_connection_pool
import logging

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)


async def get_cost(start_date: datetime, end_date: datetime) -> Dict[str,float]:
    """Use cost explorer boto3 client to get the cost metric(s) and return back the cost metrics back as smaller dictionary"""
    cost_explore_client= boto3.client("ce")
    response = cost_explore_client.get_cost_and_usage(TimePeriod={
        "Start": start_date.strftime("%Y-%m-%d"),
        "End": end_date.strftime("%Y-%m-%d")
    }, Granularity="DAILY",
    Metrics=["UnblendedCost", "NetUnblendedCost", "NetAmortizedCost"]
    #Filter={
        #"Tags":{
            #"Key": "Application",
            #"Values": ["CUE"]
        #}}
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

async def calculate_cost_per_file(files: List[FileSize], cost_per_byte: Dict[str, float]) -> List[FileCost]:
    """Calculate the per file cost for each cost metric"""
    file_costs = []
    for file in files:
        size_bytes = file.size_bytes
        fc = FileCost(id=file.id,
                      unblended_cost=size_bytes * cost_per_byte["UnblendedCost"],
                      net_unblended_cost=size_bytes * cost_per_byte["NetUnblendedCost"],
                      net_amortized_cost=size_bytes * cost_per_byte["NetAmortizedCost"])
        file_costs.append(fc)
    return file_costs

async def update_file_costs(start_date: datetime, end_date: datetime):
    pool = await get_connection_pool()
    try:
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
        cost = await get_cost(start_date, end_date)
        if cost["UnblendedCost"] == 0 or cost["NetUnblendedCost"] == 0 or cost["NetAmortizedCost"] == 0:
            logger.error('One or more cost metrics is 0')
            return
        # calculate the cost per byte
        cost_per_byte = {
            "UnblendedCost": cost["UnblendedCost"] / total_size,
            "NetUnblendedCost": cost["NetUnblendedCost"] / total_size,
            "NetAmortizedCost": cost["NetAmortizedCost"] /total_size
        }
        # calculate cost per file
        file_costs = await calculate_cost_per_file(files, cost_per_byte)

        async with pool.acquire() as conn:
            for file_cost in file_costs:
                params = (file_cost.id,
                          file_cost.model_dump_json(include={'unblended_cost', 'net_unblended_cost', 'net_amortized_cost'}))
                await update_file_status_with_cost(conn, params)
    except Exception as e:
        logger.error("Failed to update cost", exc_info=True)
    finally:
        await pool.close()
