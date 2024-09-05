import boto3

from lambda_utils.type_util.upload import upload_url_pld, upload_url_return

async def generate_upload_url(params:upload_url_pld) -> upload_url_return:
    #db action for file tracking here
    
    s3Client = boto3.client('s3')
    
    try:
        resp = s3Client.generate_presigned_post(
            Bucket="my_bucket",
            Key=params.file_name,
            Fields={
                'x-amx-meta-checksumalgorithm': 'SHA256',
                'x-amz-meta-checksum-value': params.checksum,
                'x-amz-checksum-sha256': params.checksum, 
            },
            Conditions=[
                { 'x-amz-meta-checksumalgorithm': 'SHA256' },
                { 'x-amz-meta-checksumvalue': params.checksum },
                { 'x-amz-checksum-sha256': params.checksum }
            ],
            ExpiresIn=60
        )
    except Exception as e:
        print({"error": str(e)})
        return {"message": "Error generating upload URL"}
    
    return resp