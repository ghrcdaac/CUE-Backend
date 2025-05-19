from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import query, get_connection_pool
from lambda_utils.database_util import file_metrics as file_metrics_db
from lambda_utils.type_util.file_metrics import (SummaryCostReturn, DailyCostReturn, TotalCostReturn, CostReturn, FilesMetadata)
from typing import List, Optional
from uuid import UUID 
import logging 
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

async def get_sample_summary_cost():
    return {"daily_cost": [{"date": datetime(2025,5,14), "cost":100}],
            "total_cost": {"cost":100, "start_date": datetime(2025,5,14), "end_date":datetime(2025,5,14)}, 
            "files_metadata": {"number_of_files":1, "size":"100GB", "cost_per_byte":0.9}}

async def get_sample_collection_cost():
    return [{
                "name": "collection1",
                "cost": 1.00,
                "size": "100GB"
            },
            {
                "name": "collection2",
                "cost": 1.00,
                "size": "100GB"
            }]

async def get_sample_file_cost():
    return [{
                "name": "file1",
                "cost": 10
            },
            {
                "name": "file2",
                "cost": 10
            }]
