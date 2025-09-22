import sys
import boto3
from botocore.exceptions import ClientError
import asyncpg
import structlog
from contextlib import asynccontextmanager
import pandas as pd
from pandas import DataFrame
import pyarrow as pa
import pyarrow.parquet as pq
from awsglue.utils import getResolvedOptions
import logging 
import os 
import hashlib
import asyncio
from typing import List, Tuple

DB_HOST = os.getenv("PG_HOST") # RDS_PROXY
DB_PORT = os.getenv("PG_PORT", 5432)
DB_NAME = os.getenv("PG_DB")
DB_USER = os.getenv("PG_USER")
DB_PASS = os.getenv("PG_PASS")

shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
]
processors = shared_processors + [
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.JSONRenderer(),
]
log_level = logging.INFO

logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=log_level,
)

structlog.configure(
    processors=processors,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

async def main(param_name, bucket):
    conn = None
    try:
        #  Fetch SSM parameter
        retention_period = await fetch_retention_period(param_name)
        logger.info(f"Retention Period: {retention_period}")
        async with get_db_connection() as conn:
            total_count = await get_aged_off_count(conn, retention_period)
            logger.info(f"# of metrics outside of retention period: {total_count}")
        
            if total_count == 0:
                logger.info("There no metrics outside of the retention period")
                sys.exit()

            # Depending on expected amount of files to be aged-off consider doing this in chunks
            logger.info(f"Gathering metrics outside of retention period: {retention_period}")

            # query RDS database for metrics older than retention period
            columns, metrics = await get_aged_off_metrics(conn, retention_period)

            #load records into dataframe
            df = pd.DataFrame(metrics, columns=columns)

            logger.info(f"Converting metrics into partitioned parquet files.")
            #transform upload and verify
            uploaded_metrics = await upload_to_s3(df, bucket)

            if uploaded_metrics and len(uploaded_metrics) == total_count:
                #if upload was successful delete records from database
                await remove_aged_off_metrics(conn, retention_period, uploaded_metrics)

    except Exception as e:
        logger.error(f"Failed to move aged off metrics {e}", exc_info=True)

async def fetch_retention_period(retention_period_param_name: str) -> int:
    """Fetch metric retention period from SSM"""
    try:
        ssm_client = boto3.client('ssm')
        response = ssm_client.get_parameter(Name=f'{retention_period_param_name}')
        retention_period = int(response['Parameter']['Value'])
        return retention_period
    except ValueError as ve:
        logger.error(f"Error could not convert ssm parameter into a Integer {ve}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error occurred while trying to fetch ssm parameter {e}", exc_info=True)
        raise


@asynccontextmanager
async def get_db_connection():
    """Create a connection to RDS and return the connection"""
    conn = None
    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASS]):
        logger.error("Database environment variables are not fully configured.")
        raise ValueError("Missing database configuration in environment variables.")

    ssl_mode = os.getenv("DB_SSL_MODE", "require")
    try:
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            ssl=ssl_mode
        )
        logger.debug(f"Connection acquired to {DB_HOST}")
        yield conn
    except asyncpg.PostgresError as e:
        logger.error(f"Database connection error: {e}", exc_info=True)
        # Re-raise the exception to be handled by the calling function
        raise
    finally:
        if conn and not conn.is_closed():
            await conn.close()
            logger.debug(f"Connection to {DB_HOST} closed.")

async def get_aged_off_count(conn, retention_period: int) -> int:
    """Get a count of the metrics that are being aged off """
    query = """
                SELECT count(file_status.id)
                FROM file_status 
                WHERE (DATE(NOW()) - DATE(file_status.upload_time)) >= $1 
            """
    try:
        total_count = await conn.fetchval(query, retention_period)
        #total_count = 0
        #if result:
            #total_count = result[0]

        return total_count

    except Exception as e:
        logger.error(f"Error counting aged off metrics {e}", exc_info=True)
        raise

async def get_aged_off_metrics(conn, retention_period: int) -> Tuple[List[str], List]:
    """Get the metrics data that is being aged off"""
    query = """
                SELECT f.id::text, f.name, f.type, f.cueuser_uploaded::text, f.size_bytes, f.collection_id::text, f.collection_path, f.edpub,
                       f.checksum, fs.upload_time, fs.scan_start, fs.scan_end, fs.egress_start, fs.status, fs.scan_results,
                       c.provider_id::text, c.ngroup_id::text, DATE(fs.upload_time) as date, scanner_cost, aws_transfer_cost, metric_recorded_at
                FROM 
                    file f 
                JOIN
                    file_status fs ON fs.id = f.id
                JOIN
                    cost_metric cm on cm.file_id = f.id
                JOIN 
                    collection c ON f.collection_id = c.id
                WHERE 
                    DATE(NOW()) - DATE(upload_time) >= $1 
            """
    column_names = ["id", "name", "type", "cueuser_uploaded",
                    "size_bytes", "collection_id", "collection_path", "edpub",
                    "checksum", "upload_time", "scan_start", "scan_end",
                    "egress_start", "status", "scan_results", "provider_id", "ngroup_id",
                    "date", "scanner_cost", "aws_transfer_cost", "metric_recorded_at"]
    try:
        metrics = await conn.fetch(query, retention_period)
        return column_names, metrics
    except Exception as e:
        logger.error(f"Error gathering aged off metrics {e}", exc_info=True)
        raise

async def remove_aged_off_metrics(conn, retention_period: int, ids: List[str]):
    """Remove aged off metrics from RDS"""
    query_fs = """
                DELETE FROM file_status 
                WHERE DATE(NOW()) - DATE(upload_time) >= $1 and file_status.id = $2 
             """
    try:
        for _id in ids:
            await conn.execute(query_fs, *(retention_period, _id))
    except Exception as e:
        logger.error(f"Error removing aged off metrics {e}", exc_info=True)
        raise


async def upload_to_s3(df: DataFrame, bucket: str) -> List[str]:
    """Upload metrics to s3 bucket and verify that upload was successful"""
    uploaded_metrics = []
    data_path = "/tmp/metrics"
    os.makedirs(data_path, exist_ok=True)

    parquet_schema = pa.schema([("id", pa.string()), ("name", pa.string()), ("type", pa.string()), ("cueuser_uploaded", pa.string()),
                                ("size_bytes", pa.int32()), ("collection_id", pa.string()), ("collection_path", pa.string()), ("edpub", pa.bool_()),
                                ("checksum", pa.string()), ("upload_time", pa.timestamp("us", tz="UTC")), ("scan_start", pa.timestamp("us", tz="UTC")), ("scan_end", pa.timestamp("us", tz="UTC")),
                                ("egress_start", pa.timestamp("us", tz="UTC")), ("status", pa.string()), ("scan_results", pa.string()), ("provider_id", pa.string()),
                                ("ngroup_id", pa.string()), ("date", pa.date64()), ("scanner_cost", pa.decimal128(10,6)), ("aws_transfer_cost", pa.decimal128(10,6)), ("metric_recorded_at", pa.timestamp("us", tz="UTC"))])

    s3_client = boto3.client("s3")
    for (date, collection_id, provider_id, cueuser_uploaded), group in df.groupby(["date", "collection_id", "provider_id", "cueuser_uploaded"]):
        #Create partition directory
        partition_path = os.path.join(data_path, f"date={date}/collection={collection_id}/provider={provider_id}/cueuser_uploaded={cueuser_uploaded}")
        os.makedirs(partition_path, exist_ok=True)

        #Convert Dataframe group to Parquet file
        temp_parquet_file = os.path.join(partition_path, "data.parquet")
        table = pa.Table.from_pandas(group, schema=parquet_schema)
        pq.write_table(table, temp_parquet_file)

        #Upload the Parquet file
        s3_path = f"data/metrics/date={date}/collection={collection_id}/provider={provider_id}/cueuser_uploaded={cueuser_uploaded}/data.parquet"
        md5_checksum = await calculate_md5(temp_parquet_file)
        try:
            # store in s3
            s3_client.upload_file(temp_parquet_file, bucket ,s3_path)

            # check if s3 upload was successful
            if await check_s3_file_upload(bucket, s3_path, md5_checksum):
                uploaded_metrics.extend(group['id'])
                logger.info("Successful uploaded")

        except ClientError as ce:
            logger.error(f"Error could not verify parquet existence in s3 bucket {ce}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error failed to upload parquet file to s3 bucket {e}", exc_info=True)
            raise
    return uploaded_metrics

async def calculate_md5(filepath: str) -> str:
    """Calculate the MD5 checksum of a file."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

async def check_s3_file_upload(bucket_name:str, file_key:str, md5_local:str) -> bool:
    s3_client = boto3.client("s3")
    try:
        s3_object = s3_client.head_object(Bucket=bucket_name, Key=file_key)
        md5_s3 = s3_object['ETag'].strip('"')
        
        # Check if the ETag is equal to the local MD5
        if md5_s3 == md5_local:
            return True
    except Exception as e:
        logger.error(f"Error checking file integrity: {e}", exc_info=True)

    return False


if __name__ == "__main__":
    # Read command line arguments
    args = getResolvedOptions(sys.argv, ["PG_HOST", "PG_PORT", "PG_DATABASE", "PG_USER", "PG_PASSWORD", "SSM_PARAM_NAME", "ARCHIVE_BUCKET"])
    DB_HOST = args["PG_HOST"]
    DB_PORT = args["PG_PORT"]
    DB_NAME = args["PG_DATABASE"]
    DB_USER = args["PG_USER"]
    DB_PASS = args["PG_PASSWORD"]
    ssm_param_name = args["SSM_PARAM_NAME"]
    archive_bucket = args["ARCHIVE_BUCKET"]
    logger.info("STARTING GLUE JOB")
    asyncio.run(main(ssm_param_name, archive_bucket)) #db_host, db_port, db_database, db_user, db_password, ))
    logger.info("GLUE JOB COMPLETE")
