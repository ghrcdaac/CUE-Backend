from typing import List, Dict, Any
from datetime import datetime
import os
import json
import decimal
from decimal import Decimal
import boto3
import asyncpg
from db import get_file_data, update_file_status_with_cost
from botocore.exceptions import ClientError
import structlog

from core.db_pool import get_database_pool


decimal.getcontext().prec = 10 # set decimal precision to 10 
logger = structlog.get_logger(__name__)
CSS_ROLE_ARN = str(os.getenv("CSS_ROLE_ARN", ""))

class CostUpdateError(Exception):
    pass

async def get_css_creds():
    """Use sts boto3 client to assume role CSS role and retrieve credentials"""
    try:
        sts_client = boto3.client("sts")
        assumed_role_object = sts_client.assume_role(RoleArn=CSS_ROLE_ARN, RoleSessionName="CostExplorerSession")
        credentials = assumed_role_object['Credentials']
        return credentials
    except ClientError as e:
        logger.error("css_role_credentials.retrieval.failed", error_code=e.response['Error']['Code'])
        raise CostUpdateError(e) 
    except Exception as e: 
        logger.error("css_role_credentials.retrieval.unexpected_error", error=e, exc_info=True)
        raise CostUpdateError(e)


async def get_scan_cost(start_time: datetime, end_time: datetime, granulity="DAILY") -> Dict[str, Decimal]:
    """Use cost explorer boto3 client to get the cost metrics from the css account"""
    try:
        css_creds = await get_css_creds()
        cost_explore_client = boto3.client("ce",
            aws_access_key_id=css_creds["AccessKeyId"],
            aws_secret_access_key=css_creds["SecretAccessKey"],
            aws_session_token=css_creds["SessionToken"]
        )
        response = cost_explore_client.get_cost_and_usage(
            TimePeriod={
                "Start": start_time.strftime("%Y-%m-%d"),
                "End": end_time.strftime("%Y-%m-%d")
            },
            Granularity=granulity,
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

        cost = { 
            "UnblendedCost": Decimal(0.0), 
            "NetUnblendedCost": Decimal(0.0),
            "NetAmortizedCost": Decimal(0.0)
        }
        for time_interval in response.get("ResultsByTime"):
            cost = { 
                "UnblendedCost": cost["UnblendedCost"] + Decimal(time_interval['Total']["UnblendedCost"]["Amount"]), 
                "NetUnblendedCost":cost["NetUnblendedCost"] + Decimal(time_interval['Total']["NetUnblendedCost"]["Amount"]),
                "NetAmortizedCost":cost ["NetAmortizedCost"]+ Decimal(time_interval['Total']["NetAmortizedCost"]["Amount"])
            }
        return cost
    except ClientError as e:
        logger.error("scan_cost.retrieval.failed", error_code=e.response['Error']['Code'])
        raise CostUpdateError(e)
    except Exception as e: 
        logger.error("scan_cost.retrieval.unexpected_error", error=e)
        raise CostUpdateError(e)
        

async def get_aws_cost(start_time: datetime, end_time: datetime, granularity="DAILY") -> Dict[str,Decimal]:
    """Use cost explorer boto3 client to get the cost metric(s) and return back the cost metrics back as smaller dictionary"""
    try:
        cost_explore_client = boto3.client("ce")
        response = cost_explore_client.get_cost_and_usage(
            TimePeriod={
                "Start": start_time.strftime("%Y-%m-%d"),
                "End": end_time.strftime("%Y-%m-%d")
            },
            Granularity=granularity,
            Metrics=["UnblendedCost", "NetUnblendedCost", "NetAmortizedCost"],
        )
        cost = { 
            "UnblendedCost": Decimal(0.0), 
            "NetUnblendedCost": Decimal(0.0),
            "NetAmortizedCost": Decimal(0.0)
        }
        for time_interval in response.get("ResultsByTime"):
            cost = { 
                "UnblendedCost": cost["UnblendedCost"] + Decimal(time_interval['Total']["UnblendedCost"]["Amount"]), 
                "NetUnblendedCost":cost["NetUnblendedCost"] + Decimal(time_interval['Total']["NetUnblendedCost"]["Amount"]),
                "NetAmortizedCost":cost ["NetAmortizedCost"]+ Decimal(time_interval['Total']["NetAmortizedCost"]["Amount"])
            }
        return cost
    except ClientError as e:
        logger.error("aws_cost.retrieval.failed", error_code=e.response["Error"]["Code"]) 
        raise CostUpdateError(e)
    except Exception as e:
        logger.error("aws_cost.retrieval.unexpected_error")
        raise CostUpdateError(e)

async def calculate_cost_per_file(files: List[Dict[str,Any]], type:str, cost_per_byte: Dict[str, Decimal]) -> List[tuple]:
    """Calculate the per file cost for each cost metric"""
    file_costs = []
    logger.info(f"Decimal precision: {decimal.getcontext().prec}")
    for file in files:
        logger.info(file)
        file_id = file.get('file_id')
        size_bytes = file['file_size']
        fc = ( 
                file_id,
                json.dumps({
                    "type":type,
                    "unblended_cost": float((size_bytes * cost_per_byte["UnblendedCost"]).quantize(Decimal("0.000001"))),
                    "net_unblended_cost": float((size_bytes * cost_per_byte["NetUnblendedCost"]).quantize(Decimal("0.000001")))
                    #"net_amortized_cost":size_bytes * cost_per_byte["NetAmortizedCost"]
                })
            )
        file_costs.append(fc)
    return file_costs

async def update_file_costs(start_time:datetime, end_time:datetime, pool:asyncpg.Pool):
    try:
        pool = await get_database_pool()
        if not pool:
            logger.critical("db.pool.not_available.failing_invocation")

        async with pool.acquire() as conn:
            # get file and total upload volume of within time range
            file_data = await get_file_data(conn, (start_time, end_time))
        
        total_size = file_data.get("total_size", 0)
        files = file_data.get("files",[])
        logger.info(type(files[0]))
        files = [json.loads(file) for file in files]
        if total_size == 0 or len(files) == 0:
            logger.info("No files to update cost for")
            return
            
        # get the cost
        # Cost Explorer data is updated at least once every 24 hours some data might be updated later 
        scan_cost = await get_scan_cost(start_time, end_time)
        aws_cost = await get_aws_cost(start_time, end_time)

        logger.info(f"Scan cost: {scan_cost}")
        logger.info(f"AWS cost: {aws_cost}")

        # UnblendedCost - Represents usage cost 
        # NetUnblendedCost - Represents the usage cost after discounts
        # NetAmortizedCost - Represents the effective cost of the upfront
        #  and monthly reservation fees spread across the billing period.
        #  Costs are broken out into the effective daily rate. 
        #  UnblendedCost + Amortized portion of upfront and recurring reservation fees
        #  including discounts.

        # calculate the cost per byte
        scan_cost_per_byte = {
            "UnblendedCost": scan_cost["UnblendedCost"] / total_size if scan_cost["UnblendedCost"] > 0.0 else Decimal(0.0),
            "NetUnblendedCost": scan_cost["NetUnblendedCost"] / total_size if scan_cost["NetUnblendedCost"] > 0.0 else Decimal(0.0)
            #"NetAmortizedCost": scan_cost["NetAmortizedCost"] /total_size if scan_cost["NetAmortizedCost"] > 0.0 else Decimal(0.0),
        }

        aws_cost_per_byte = {
            "UnblendedCost": aws_cost["UnblendedCost"] / total_size if aws_cost["UnblendedCost"] > 0.0 else Decimal(0.0),
            "NetUnblendedCost": aws_cost["NetUnblendedCost"] / total_size if aws_cost["NetUnblendedCost"] > 0.0 else Decimal(0.0)
            #"NetAmortizedCost": aws_cost["NetAmortizedCost"] /total_size if aws_cost["NetAmortizedCost"] > 0.0 else Decimal(0.0),
        }

        # calculate cost per file
        scan_file_costs = await calculate_cost_per_file(files, "scan", scan_cost_per_byte)
        aws_file_costs = await calculate_cost_per_file(files, "aws", aws_cost_per_byte)

        async with pool.acquire() as conn: 
            await update_file_status_with_cost(conn, scan_file_costs)
            await update_file_status_with_cost(conn, aws_file_costs)
    except Exception as e:
        logger.error("Failed to update cost", exc_info=True)
        raise e
