import sys
import boto3
from botocore.exceptions import ClientError
from psycopg2 import connect
import pandas as pd
from pandas import DataFrame
import pyarrow as pa
import pyarrow.parquet as pq
from awsglue.utils import getResolvedOptions
import logging 
import os 
import hashlib
from typing import List, Tuple

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def main(host: str, port: str, database: str, user: str, password: str, param_name: str, bucket: str):
    conn = None
    try:
        #  Fetch SSM parameter
        retention_period = fetch_retention_period(param_name)
        logger.info(f"Retention Period: {retention_period}")
        # Connect to RDS
        conn = get_connection_to_rds(host, port, database, user, password)
        logger.info("Acquired connection to RDS.")

        total_count = get_aged_off_count(conn, retention_period)
        logger.info(f"# of metrics outside of retention period: {total_count}")
        
        if total_count == 0:
            logger.info("There no metrics outside of the retention period")
            sys.exit()

        # Depending on expected amount of files to be aged-off consider doing this in chunks
        logger.info(f"Gathering metrics outside of retention period: {retention_period}")

        # query RDS database for metrics older than retention period
        columns, metrics = get_aged_off_metrics(conn, retention_period)
        print(metrics)

        #load records into dataframe
        df = pd.DataFrame(metrics, columns=columns)

        logger.info(f"Converting metrics into partitioned parquet files.")
        #transform upload and verify
        uploaded_metrics = upload_to_s3(df, bucket)

        if uploaded_metrics and len(uploaded_metrics) == total_count:
            #if upload was successful delete records from database
            remove_aged_off_metrics(conn, retention_period, uploaded_metrics)

    except Exception as e:
        logger.error(f"Failed to move aged off metrics {e}", exc_info=True)

    finally:
        if conn is not None:
            conn.close()

def fetch_retention_period(retention_period_param_name: str) -> int:
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



def get_connection_to_rds(host: str, port: str, database: str, user: str, password: str):
    """Create a connection to RDS and return the connection"""
    try:
        # Connect to RDS instance
        connection = connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        return connection
    except Exception as e:
        logger.error(f"Error connecting to RDS: {e}", exc_info=True)
        raise

def get_aged_off_count(conn, retention_period: int) -> int:
    """Get a count of the metrics that are being aged off """
    query = """
                SELECT count(file_status.id)
                FROM file_status 
                WHERE (DATE(NOW()) - DATE(file_status.upload_time)) >= %s
            """
    try:
        with conn:
            with conn.cursor() as curs:
                curs.execute(query, (retention_period,))
                result = curs.fetchone()
                total_count = 0
                if result:
                    total_count = result[0]

                return total_count

    except Exception as e:
        logger.error(f"Error counting aged off metrics {e}", exc_info=True)
        raise

def get_aged_off_metrics(conn, retention_period: int) -> Tuple[List[str], List]:
    """Get the metrics data that is being aged off"""
    query = """
                SELECT f.id, f.name, f.type, f.cueuser_uploaded, f.size_bytes, f.collection_id, f.collection_path, f.edpub,
                       f.checksum, fs.upload_time, fs.scan_start, fs.scan_end, fs.egress_start, fs.status, fs.scan_results,
                       c.provider_id, DATE(fs.upload_time) as date
                FROM 
                    file f 
                JOIN
                    file_status fs ON fs.id = f.id
                JOIN 
                    collection c ON f.collection_id = c.id
                WHERE 
                    DATE(NOW()) - DATE(upload_time) >= %s 
            """
    column_names = ["id", "name", "type", "cueuser_uploaded",
                    "size_bytes", "collection_id", "collection_path", "edpub",
                    "checksum", "upload_time", "scan_start", "scan_end",
                    "egress_start", "status", "scan_results", "provider_id",
                    "date"]
    try:
        with conn:
            with conn.cursor() as curs:
                curs.execute(query, (retention_period,))
                metrics = curs.fetchall()
                return column_names, metrics
    except Exception as e:
        logger.error(f"Error gathering aged off metrics {e}", exc_info=True)
        raise

def remove_aged_off_metrics(conn, retention_period: int, ids: List[str]):
    """Remove aged off metrics from RDS"""
    query_fs = """
                DELETE FROM file_status 
                WHERE DATE(NOW()) - DATE(upload_time) >= %s and file_status.id = %s
             """
    query_file = """
                DELETE FROM file
                WHERE file.id = %s 
             """
    try:
        with conn:
            with conn.cursor() as curs:
                for _id in ids:
                    curs.execute(query_fs, (retention_period, _id))
                    curs.execute(query_file, (_id,))
    except Exception as e:
        logger.error(f"Error removing aged off metrics {e}", exc_info=True)
        raise


def upload_to_s3(df: DataFrame, bucket: str) -> List[str]:
    """Upload metrics to s3 bucket and verify that upload was successful"""
    uploaded_metrics = []
    data_path = "/tmp/metrics"
    os.makedirs(data_path, exist_ok=True)

    s3_client = boto3.client("s3")
    for (date, collection_id, provider_id, cueuser_uploaded), group in df.groupby(["date", "collection_id", "provider_id", "cueuser_uploaded"]):
        #Create partition directory
        partition_path = os.path.join(data_path, f"date={date}/collection={collection_id}/provider={provider_id}/cueuser={cueuser_uploaded}")
        os.makedirs(partition_path, exist_ok=True)

        #Convert Dataframe group to Parquet file
        temp_parquet_file = os.path.join(partition_path, "data.parquet")
        table = pa.Table.from_pandas(group)
        pq.write_table(table, temp_parquet_file)

        #Upload the Parquet file
        s3_path = f"/data/date={date}/collection={collection_id}/provider={provider_id}/cueuser_uploaded={cueuser_uploaded}/data.parquet"
        md5_checksum = calculate_md5(temp_parquet_file)
        try:
            # store in s3
            s3_client.upload_file(temp_parquet_file, bucket ,s3_path)

            # check if s3 upload was successful
            if check_s3_file_upload(bucket,s3_path, md5_checksum):
                uploaded_metrics.extend(group['id'])
                logger.info("Successful uploaded")

        except ClientError as ce:
            logger.error(f"Error could not verify parquet existence in s3 bucket {ce}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error failed to upload parquet file to s3 bucket {e}", exc_info=True)
            raise
    return uploaded_metrics

def calculate_md5(filepath: str) -> str:
    """Calculate the MD5 checksum of a file."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def check_s3_file_upload(bucket_name:str, file_key:str, md5_local:str) -> bool:
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
    args = getResolvedOptions(sys.argv, ["DB_HOST", "DB_PORT", "DB_DATABASE", "DB_USER", "DB_PASSWORD", "SSM_PARAM_NAME", "ARCHIVE_BUCKET"])

    db_host = args["DB_HOST"]
    db_port = args["DB_PORT"]
    db_database = args["DB_DATABASE"]
    db_user = args["DB_USER"]
    db_password = args["DB_PASSWORD"]
    ssm_param_name = args["SSM_PARAM_NAME"]
    archive_bucket = args["ARCHIVE_BUCKET"]

    main(db_host, db_port, db_database, db_user, db_password, ssm_param_name, archive_bucket)
