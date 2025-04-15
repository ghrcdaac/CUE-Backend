import os
import boto3
from fastapi import HTTPException

from asyncpg.pool import Pool
from datetime import datetime, timezone
from lambda_utils.database_util.db_util import get_connection_pool
from lambda_utils.database_util import file as file_db
from lambda_utils.database_util import file_status as file_status_db
from lambda_utils.database_util import collection as collection_db

from lambda_utils.type_util.upload import upload_url_pld, upload_url_return
from lambda_utils.type_util.cueuser_auth import CueuserAuthBearer

async def generate_upload_url(params:upload_url_pld, user:CueuserAuthBearer) -> upload_url_return:
    #db action for file tracking here

    pool: Pool = await get_connection_pool()
    conn = await pool.acquire()
    try:
        async with conn.transaction():
            payload = (
                params.collection,
                user['ngroup_id']
            )
            
            collection_resp = await collection_db.get_collection_by_lookup_from_db(conn, payload)
            if collection_resp == []:
                raise(HTTPException(status_code=400, detail="Collection not found"))
            
            payload = (
                params.file_name, 
                params.file_type, 
                user['id'], 
                params.size,
                collection_resp[0][0], # collection id
                False,
                params.checksum
            )
            resp = await file_db.create_file_in_db(conn, payload)
            payload = (
                resp[0], # file id
                datetime.now(timezone.utc),
                'unscanned',
                None
            )
            _  = await file_status_db.create_file_status_in_db(conn, payload)
    except Exception as e:
        print(e)
        raise(HTTPException(status_code=500, detail="Error creating file in database"))
    finally:
        await pool.release(conn)
    
    payload = (params.file_name, 
               params.file_type, 
               user['cueusername'], 
               params.size,
               params.collection_path,
               False,
               params.checksum
    ) 
    if os.environ.get("ENV") == "dev":
        s3Client = boto3.client('s3',
                                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
                                region_name="us-west-2"
        )
    else:
        s3Client = boto3.client('s3')
    
    try:
        resp = s3Client.generate_presigned_post(
            Bucket="cue-sit-dmz",
            Key=f"{resp[0]}", # file id
            Fields={
                'x-amz-checksum-sha256': params.checksum
            },
            Conditions=[
                { 'x-amz-checksum-sha256': params.checksum }
            ],
            ExpiresIn=60
        )
    except Exception as e:
        print(e)
        raise(HTTPException(status_code=500, detail="Error generating upload URL"))
    
    return resp