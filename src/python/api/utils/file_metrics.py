from asyncpg.pool import Pool
from lambda_utils.database_util.db_util import get_connection_pool
from lambda_utils.database_util import file_metrics as file_metrics_db
from lambda_utils.type_util.file_metrics import SummaryCostReturn, CostReturn, MetricsQueryParameters
from typing import List, Tuple
from uuid import UUID 
import logging 
from datetime import datetime, timedelta, date
from decimal import Decimal, getcontext, ROUND_UP
from math import ceil

logger = logging.getLogger(__name__)
decimal_context = getcontext()
decimal_context.rounding=ROUND_UP

# temporary values for cost calculation
AWS_COST = Decimal(0.00001)
SCAN_COST = Decimal(0.00005)

def format_to_GB(bytes:int) -> str:
    """Helper function to format size into GB string"""
    gbs = Decimal(bytes / (1024**3)) if bytes > 0 else Decimal(0)
    return f"{gbs:.2f}GB"


async def get_summary_cost(ngroup_id:UUID, params: MetricsQueryParameters) -> SummaryCostReturn:
    """Retrieve metrics and calculate summary costs."""
    pool: Pool = await get_connection_pool()
    conn = None

    if params.start_date is None:
        params.start_date = date.today()

    if params.end_date is None:
        params.end_date = params.start_date + timedelta(days=7)

    filters_dict = params.model_dump(exclude_none=True)
    try:
        async with pool.acquire() as conn:
           daily_metrics = await file_metrics_db.get_daily_metrics(conn, ngroup_id ,filters_dict)
    except Exception as e:
        logger.error(f"Error retrieving summary metrics: {e}", exc_info=True)
        raise

    try:
        # calculate results
        daily_cost = []
        _total_cost = Decimal(0)
        total_size = Decimal(0)
        total_file_count = 0
        for record in daily_metrics:
            size = Decimal(record.get("size"))
            aws_cost = size * AWS_COST
            scan_duration = record.get("scan_duration")
            scan_cost = scan_duration * SCAN_COST if scan_duration else 0
            cost = aws_cost + scan_cost
            cost = cost.quantize(Decimal(0.00))
            _date = datetime.strftime(record.get("date"), "%Y-%m-%d")
            daily_cost.append({"date": _date, "cost": cost})
            _total_cost += cost
            total_size += size
            total_file_count += record.get("file_count")

        total_cost = {"cost": _total_cost.quantize(Decimal(0.00)), "start_date": params.start_date, "end_date": params.end_date}
        cost_per_byte = Decimal(0)
        if _total_cost > 0 and total_size > 0:
            cost_per_byte = Decimal(_total_cost/total_size)

        cost_per_byte = cost_per_byte.quantize(Decimal(0.00))
        files_metadata = {
            "number_of_files": total_file_count,
            "size": format_to_GB(total_size),
            "cost_per_byte": cost_per_byte,
        }

        return {"daily_cost": daily_cost,
                "total_cost": total_cost,
                "files_metadata": files_metadata}
    except Exception as e:
        logger.error(f"Error calculating summary costs: {e}", exc_info=True)

async def get_cost_collection(ngroup_id:UUID, params: MetricsQueryParameters,  page:int, page_size:int) -> Tuple[List[CostReturn], int, int]:
    """Retrieve metrics and calculate collection costs."""
    pool: Pool = await get_connection_pool()
    conn = None

    if params.start_date is None:
        params.start_date = date.today()

    if params.end_date is None:
        params.end_date = params.start_date + timedelta(days=7)

    offset = (page - 1) * page_size
    filters_dict = params.model_dump(exclude_none=True)

    collection_metrics = []
    metrics_count = 0
    pages = 0

    try:
        async with pool.acquire() as conn:
            metrics_count = await file_metrics_db.count_collection_metrics(conn, ngroup_id, filters_dict)
            if metrics_count > 0 and offset < metrics_count:
                collection_metrics = await file_metrics_db.get_collection_metrics(conn, ngroup_id, filters_dict, page_size, offset)
                pages = ceil(metrics_count / page_size)

    except Exception as e:
        logger.error(f"Error retrieving collection metrics: {e}", exc_info=True)
        raise

    try:
        # calculate result
        collection_cost = []
        for record in collection_metrics:
            scan_duration = record.get('scan_duration')
            size = Decimal(record.get('size'))
            aws_cost = size * AWS_COST
            scan_cost = scan_duration * SCAN_COST if scan_duration else 0
            cost = aws_cost + scan_cost
            cost = cost.quantize(Decimal(0.00))
            collection_cost.append(
                                        {
                                            "name": record.get("name"),
                                            "size": format_to_GB(size),
                                            "cost": cost,
                                        }
                                )
        return collection_cost, metrics_count, pages
    except Exception as e:
        logger.error(f"Error calculating collection costs: {e}", exc_info=True)

async def get_cost_file(ngroup_id:UUID, params: MetricsQueryParameters,  page:int, page_size:int) -> Tuple[List[CostReturn], int, int]:
    """Retrieve metrics and calculate file costs."""
    pool: Pool = await get_connection_pool()
    conn = None

    if params.start_date is None:
        params.start_date = date.today()

    if params.end_date is None:
        params.end_date = params.start_date + timedelta(days=7)

    offset = (page - 1) * page_size
    filters_dict = params.model_dump(exclude_none=True)

    file_metrics = []
    metrics_count = 0
    pages = 0

    try:
        async with pool.acquire() as conn:
            metrics_count = await file_metrics_db.count_file_metrics(conn, ngroup_id, filters_dict)
            if metrics_count > 0 and offset < metrics_count:
                file_metrics = await file_metrics_db.get_file_metrics(conn, ngroup_id, filters_dict, page_size, offset)
                pages = ceil(metrics_count / page_size)

    except Exception as e:
        logger.error(f"Error retrieving file metrics {e}", exc_info=True)
        raise

    try:
        # calculate results
        file_cost = []
        for record in file_metrics:
            scan_duration = record.get('scan_duration')
            size = Decimal(record.get('size'))
            aws_cost = size * AWS_COST
            scan_cost = scan_duration * SCAN_COST if scan_duration else 0
            cost = aws_cost + scan_cost
            cost = cost.quantize(Decimal(0.00))
            file_cost.append(
                {
                    "name": record.get("name"),
                    "size": format_to_GB(size),
                    "cost": cost,
                }
            )
        return file_cost, metrics_count, pages

    except Exception as e:
        logger.error(f"Error calculating file costs: {e}", exc_info=True)
        raise