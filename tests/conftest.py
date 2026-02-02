import pytest
from fastapi import FastAPI
from fastapi import Request
from urllib.parse import urlparse, urlencode
import csv
import os
import uuid
import boto3
import httpx
import re
import io
from urllib.parse import parse_qs
from datetime import datetime, timezone, timedelta 
from botocore.response import StreamingBody
from unittest.mock import MagicMock, AsyncMock

from tests.fixtures.db import * 
from tests.fixtures.collection import *
from tests.fixtures.cueuser import * 
from tests.fixtures.provider import * 
from tests.fixtures.upload import * 
from tests.fixtures.user_application import * 

# Set environment variables for testing
os.environ['PG_DB'] = os.getenv('PG_DB_TEST', 'your_test_database_name')
os.environ['PG_USER'] = os.getenv('PG_USER_TEST', 'your_test_database_user')
os.environ['PG_PASS'] = os.getenv('PG_PASS_TEST', 'your_test_database_password')
os.environ['PG_HOST'] = os.getenv('PG_HOST_TEST', 'your_test_database_host')
os.environ['PG_PORT'] = os.getenv('PG_PORT_TEST', '5432')  # Ensure this is a string

os.environ['KEYCLOAK_ISSUER'] = 'https://localhost/realms/cue'
os.environ['KEYCLOAK_ADMIN_CLIENT_ID'] = 'cue-test'
os.environ['KEYCLOAK_ADMIN_CLIENT_SECRET'] = 'mock_client_secret'
os.environ['FRONTEND_CALLBACK_URL'] = 'http://localhost:3000/callback'

# Set an environment variable for the test ngroup ID
os.environ['TEST_NGROUP_ID'] = str(uuid.uuid4())

# Lambda environment variables
os.environ['QUEUE_URL'] = "https://sqs.us-west2.amazonaws.com/012345678912/mock-file-transfer-queue"
os.environ['FILE_TRANSFER_LAMBDA_NAME'] = "cue_file_transfer"
os.environ['TRANSFER_INVOCATION_MODE'] = "LAMBDA"

os.environ["INFECTED_FILE_THRESHOLD"] = "5"
os.environ["BLOCKING_LOOKBACK_HOURS"] = "24"

os.environ["CSS_ROLE_ARN"] = "css_ce_role_test"

os.environ['STAGING_BUCKET'] = "cue_staging_test"
os.environ['RESULTS_BUCKET'] = "cue_results_test"
os.environ['EMAIL_SENDER_ARN'] = "cue_email_sender"

os.environ["DLQ_URL"] = "cue_scan_results_dlq"
os.environ["SOURCE_QUEUE_URL"] = "cue_scan_results"
os.environ["MAX_SECONDS"] = "1"

os.environ['NOTIFICATION_MANAGER_ARN'] = "cue_notification_manager"
os.environ['PROCESS_ATHENA_QUERY_ARN'] = "cue_process_athena_query"
os.environ['COST_UPDATE_ARN'] = "cue_cost_update"

class MockKeyCloakAPI:
   base_url = os.getenv("KEYCLOAK_ISSUER", "")
   token_url = f"{base_url}/protocol/openid-connect/token"
   auth_url = f"{base_url}/protocol/openid-connect/auth"
   admin_api_url = f"{base_url.replace('/realms/', '/admin/realms/')}"
   users_url = f"{admin_api_url}/users"
   introspection_endpoint = f"{base_url}/protocol/openid-connect/token/introspect"

async def mock_handler(request):
    request_url = str(request.url)
    method = request.method.upper()
    path = request.url.path
    params = dict(request.url.params)  

    if request_url == MockKeyCloakAPI.token_url and method == "POST":
        params = parse_qs(request.content.decode("utf-8"))
        grant_type = params['grant_type'][0]
        if grant_type == "authorization_code": 
             return httpx.Response(200, json={
                     "access_token": "ey.mock.exchanged.jwt",
                     "expires_in": 300,
                     "refresh_expires_in": 1800,
                     "refresh_token": "ey.mock.refresh.jwt",
                     "token_type": "Bearer",
                    })
        elif grant_type == "client_credentials": 
            return httpx.Response(200, json={
                    "access_token": "ey.mock.client.credentials.jwt",
                    "token_type": "Bearer",
                    "expires_in": 300,
                    "scope": "read write"
                   })
        elif grant_type == "refresh_token": 
            return httpx.Response(200, json={
                    "access_token": "ey.mock.new.access.jwt",
                    "expires_in": 300,
                    "refresh_expires_in": 1800,
                    "refresh_token": "ey.mock.new.refresh.jwt",
                    "token_type": "Bearer",
                    "not-before-policy": 0,
                    "session_state": "b6f2c0d5-2c6d-4c7f-9a9d-1234567890ab",
                    "scope": "openid profile email",
                    "id_token": "ey.mock.id.jwt"
                   })
        else: 
            raise RuntimeError("Unsupported grant_type")

    elif request_url ==  MockKeyCloakAPI.users_url and method == "POST":
        #params = json.loads(request.content.decode("utf-8") or "{}")
        id = uuid.uuid4()
        location_url = f"{MockKeyCloakAPI.users_url}/{id}"
        return httpx.Response(201, headers={"Location":location_url})

    elif request_url ==  MockKeyCloakAPI.users_url and request.method == "GET":
        id = uuid.uuid4()
        return httpx.Response(200, json=[
                {
                    "id": "b6f2c0d5-2c6d-4c7f-9a9d-1234567890ab",
                    "username": "mock_user",
                    "firstName": "mock",
                    "lastName": "mock",
                    "email": "mock@example.com",
                    "enabled": True,
                    "emailVerified": True,
                    "createdTimestamp": 1699999999000,
                    "attributes": {},
                    "requiredActions": [],
                    "groups": []
                }
            ]
        )

    if re.match(rf"{MockKeyCloakAPI.users_url}/[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}", request_url):
        if request.method == "DELETE":
            return httpx.Response(204)
        elif request.method == "PUT" and "redirect_uri" in params:
            return httpx.Response(204)
        else:
            raise RuntimeError("Unsupported method")

    elif request_url == MockKeyCloakAPI.introspection_endpoint:
        if request.method == "POST":
            return httpx.Response(200, json={"mock_key": "mock_data"})
    else:
        RuntimeError("Trying to request unsupported url")

@pytest.fixture(scope="function")
def app() -> FastAPI:
    app = FastAPI()
    transport = httpx.MockTransport(mock_handler)
    app.state.http_client = httpx.AsyncClient(transport=transport)
    return app

@pytest.fixture
def make_request(app, connection_pool):
    """
    Build a FastAPI/Starlette Request from a minimal ASGI scope.
    Example:
        req = make_request(
            method="POST",
            url="http://testserver/items?x=1",
            headers={"authorization": "Bearer abc"},
            cookies={"session": "xyz"},
            body=b'{"name":"foo"}',
        )
    """
    def _make_request(
        method: str = "GET",
        url: str = "http://testserver/",
        headers: dict | None = None,
        cookies: dict | None = None,
        query: dict | str | None = None,
        body: bytes | str | None = None,
        client: tuple[str, int] = ("127.0.0.1", 1234),
    ) -> Request:
        parsed = urlparse(url)
        # Build query string
        if isinstance(query, dict):
            query_string = urlencode(query).encode()
        elif isinstance(query, str):
            query_string = query.encode()
        else:
            query_string = parsed.query.encode()

        # Build headers list of (lowercase-bytes, bytes)
        hdrs = [(b"host", parsed.netloc.encode() or b"testserver")]
        if headers:
            hdrs += [(k.lower().encode(), str(v).encode()) for k, v in headers.items()]
        if cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            hdrs.append((b"cookie", cookie_str.encode()))

        # Body handling
        if isinstance(body, str):
            body_bytes = body.encode()
        elif isinstance(body, bytes):
            body_bytes = body
        else:
            body_bytes = b""

        if body_bytes and not any(k == b"content-type" for k, _ in hdrs):
            hdrs.append((b"content-type", b"application/json"))
        if body_bytes:
            hdrs.append((b"content-length", str(len(body_bytes)).encode()))

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "scheme": parsed.scheme or "http",
            "path": parsed.path or "/",
            "raw_path": (parsed.path or "/").encode(),
            "query_string": query_string,
            "root_path": "",
            "headers": hdrs,
            "client": client,
            "server": (parsed.hostname or "testserver", parsed.port or (443 if (parsed.scheme or "http") == "https" else 80)),
            "app": app
        }

        async def receive():
            # Single http.request event carrying the full body
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        request = Request(scope, receive)
        request.state.pool = connection_pool
        return request 

    return _make_request

@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")

@pytest.fixture(scope="function")
def mock_boto3_client(monkeypatch):
    clients = {}

    def _get_client(name, *args, **kwargs):
        if name in clients:
            return clients[name]
        c = MagicMock(name=name)
        clients[name] = c
        return c

    s3 = _get_client("s3")
    def generate_presigned_url(method, Params=None, ExpiresIn=None, *args, **kwargs):
        assert method and method.strip() != ""
        assert ExpiresIn and isinstance(ExpiresIn, int) 
        bucket = (Params or {}).get("Bucket", "bucket")
        key = (Params or {}).get("Key", "key")
        return "http://localhost/mock_presigned_url"
    s3.generate_presigned_url.side_effect = generate_presigned_url

    def create_multipart_upload(Bucket="", Key="", ContentType="", *args, **kwargs):
        assert Bucket and Bucket.strip() != ""
        assert Key and Key.strip() != ""
        assert ContentType and ContentType != ""
        return {"UploadId": "mock_upload_id"}
    s3.create_multipart_upload.side_effect = create_multipart_upload

    def complete_multipart_upload(Bucket="", Key="", UploadId="", MultipartUpload={}, *args, **kwargs):
        assert Bucket and Bucket.strip() != ""
        assert Key and Key.strip() != ""
        assert UploadId and UploadId != ""
        return {
            'Location': 'mock_location',
            'Bucket': Bucket,
            'Key': Key,
            'Expiration': 'mock_expiration',
            'ETag': 'mock_etag',
            'ChecksumCRC32': 'mock_checksum_cr32',
            'ChecksumCRC32C': 'mock_checksum_crc32c',
            'ChecksumCRC64NVME': 'mock_checksum_crc64nvme',
            'ChecksumSHA1': 'mock_checksum_sha1',
            'ChecksumSHA256': 'mock_checksum_sha256',
            'ChecksumType': 'mock_checksum_type',
            'ServerSideEncryption': 'mock_server_side_encryption',
            'VersionId': 'mock_version_id',
            'SSEKMSKeyId': 'mock_ssemks_key_id',
            'BucketKeyEnabled': True,
            'RequestCharged': 'requester'
        }
    s3.complete_multipart_upload.side_effect = complete_multipart_upload

    def abort_multipart_upload(Bucket="", Key="", UploadId="", *args, **kwargs):
        assert Bucket and Bucket.strip() != ""
        assert Key and Key.strip() != ""
        assert UploadId and UploadId != ""
        return {"RequestCharged": "requester"}
    s3.abort_multipart_upload.side_effect = abort_multipart_upload

    def get_object(Bucket="", Key="", *args, **kwargs):
        assert Bucket and Bucket.strip()!= ""
        assert isinstance(Key, uuid.UUID) or (Key and Key.strip() != "")
        body_content = '{"mock_key":"mock_value"}'
        if Bucket=="cue-results-test":
            data  = [["id","name","status"],
                     ["mock_id1","file1","distributed"],
                     ["mock_id2","file2","infected"]]
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerows(data)
            
            body_content = output.getvalue() 
        body = StreamingBody(io.BytesIO(body_content.encode()), len(body_content.encode()))
        return {"Body":body}
    s3.get_object.side_effect = get_object

    def put_object(Bucket="", Key="", *args, **kwargs):
        assert Bucket and Bucket.strip()!= ""
        assert isinstance(Key, uuid.UUID) or (Key and Key.strip() != "")
        return {
                'Expiration': 'mock_expiration',
                'ETag': 'mock_etag_string',
                'ChecksumCRC32': 'mock_checksum_crc32',
                'ChecksumCRC32C': 'mock_checksumcrc32c',
                'ChecksumCRC64NVME': 'mock_checksumcrc64NVME',
                'ChecksumSHA1': 'mock_checksum_sha1',
                'ChecksumSHA256': 'mock_checksum_SHA256',
                'ChecksumType': 'FULL_OBJECT',
                'ServerSideEncryption': 'AES256',
                'VersionId': 'mock_version_id',
                'SSECustomerAlgorithm': 'mock_see_customer_algorithm',
                'SSECustomerKeyMD5': 'mock_sse_customer_key_md5',
                'SSEKMSKeyId': 'mock_ssekm_key_id', 'SSEKMSEncryptionContext': 'mock_sskm_encryption_context', 'BucketKeyEnabled': True, 'Size': 123, 'RequestCharged': 'requester' }
    s3.put_object.side_effect = put_object

    def copy_object(CopySource={},Bucket="",Key="",ACL="", *args, **kwargs):
        assert isinstance(CopySource,str) or isinstance(CopySource, dict) 
        if isinstance(CopySource, dict):
            assert CopySource.get("Bucket")
            assert CopySource.get("Key")
        assert isinstance(Bucket,str) and Bucket.strip() != ""
        assert isinstance(Key,str) and Key.strip() != ""
        assert ACL=="" or ACL=="bucket-owner-full-control"
        return {"CopyObjectResult":{
                    'ETag': 'mock_etag',
                    'LastModified': datetime.now(tz=timezone.utc),
                    'ChecksumType': 'FULL_OBJECT',
                    'ChecksumCRC32': 'mock_checksum_crc32',
                    'ChecksumCRC32C': 'mock_checksum_cr32c',
                    'ChecksumCRC64NVME': 'mock_checksum_crc64nvme',
                    'ChecksumSHA1': 'mock_checksum_sha1',
                    'ChecksumSHA256': 'mock_checksum_sha256'
                },
                "Expiration": "mock_expiration_id",
                "CopySourceVersionId": "mock_source_version_id",
                "VersionId": "mock_version_id",
                "ServerSideEncryption": "AES256",
                "SSECustomerAlgorithm": "AES256",
                "SSECustomerKeyMD5": "mock_md5",
                "SSEKMSKeyId": "mock_sse_kms_key_id",
                "SSEKMSEncryptionContext": "mock_sse_kms_encryption_context",
                "BucketKeyEnabled": False,
                "RequestCharged": "requester"}
    s3.copy_object.side_effect = copy_object

    def head_object(Bucket="", Key="", *args, **kwargs):
        assert isinstance(Bucket,str) and Bucket.strip() != ""
        assert isinstance(Key,str) and Key.strip() != ""
        return {"mock_header":"mock_value"}
    s3.head_object.side_effect = head_object

    def put_object_tagging(Bucket="", Key="", Tagging={}, *args, **kwargs):
        assert isinstance(Bucket,str) and Bucket.strip() != ""
        assert isinstance(Key,str) and  Key.strip() != ""
        assert isinstance(Tagging, dict) and Tagging.get("TagSet")
        return {"VersionId":"mock_version_id"}        
    s3.put_object_tagging.side_effect = put_object_tagging

    events = _get_client("events")
    def put_events(Entries=[{}], *args, **kwargs):
        failed_entries = len([entry == {} for entry in Entries])
        return { 'FailedEntryCount': failed_entries,
                 'Entries': Entries,
                 'EventId': 'mock_eventId',
                 'ErrorCode': 'mock_error_code',
                 'ErrorMessage': 'mock_error_message'
        }
    events.put_events.side_effect = put_events

    athena = _get_client("athena")
    def start_query_execution(QueryString="", QueryExecutionContext=None, ResultConfiguration=None, ResultReuseConfiguration=None, *args, **kwargs):
        assert isinstance(QueryString,str) and QueryString.strip() != ""
        assert isinstance(QueryExecutionContext, dict)
        assert isinstance(ResultConfiguration, dict)
        assert ResultReuseConfiguration and isinstance(ResultReuseConfiguration, dict)
        return {"QueryExecutionId":str(uuid.uuid4())}
    athena.start_query_execution.side_effect = start_query_execution

    def get_query_execution(QueryExecutionId=None):
        assert QueryExecutionId
        return {"QueryExecution":{"Status":{"State":"SUCCEEDED", "StateChangeReason":"testing"},"ResultConfiguration":{"OutputLocation":"'s3://cue-results-test/12345678-90ab-cdef-1234-567890abcdef.csv"}}}
    athena.get_query_execution.side_effect = get_query_execution

    lambda_ = _get_client("lambda")
    def invoke(FunctionName="", InvocationType="RequestResponse", Payload={}, *args, **kwargs):
        assert isinstance(FunctionName,str) and FunctionName.strip != ""
        assert InvocationType == "RequestResponse" or InvocationType=="Event"
        assert Payload
        payload_content = ""
        if FunctionName == "cue_manual_file_transfer":
            payload_content = '{"status_code": 200, "message": "All file transfers initiated."}'
        elif FunctionName == "cue_file_transfer":
            payload_content = '{"batchItemFailures":[]}'
        else:
            payload_content = '{}'
        payload = StreamingBody(io.BytesIO(payload_content.encode()), len(payload_content.encode()))
        return {"Payload": payload, "ResponseMetadata":{"RequestId": str(uuid.uuid4())}}
    lambda_.invoke.side_effect = invoke

    sqs = _get_client("sqs")
    def send_message(QueueUrl="", MessageBody="", *args, **kwargs):
        assert isinstance(QueueUrl, str) and QueueUrl.strip() != ""
        assert isinstance(MessageBody, str) and MessageBody.strip() != ""
        return {
                'MD5OfMessageBody': 'mock_md5_of_message_body',
                'MD5OfMessageAttributes': 'mock_md5_of_message_attributes',
                'MD5OfMessageSystemAttributes': 'mock_md5_of_message_system_attributes',
                'MessageId': str(uuid.uuid4()),
                'SequenceNumber': 'mock_sequence_number'
            }
    sqs.send_message.side_effect = send_message

    def receive_message(QueueUrl="", MaxNumberOfMessages=None,
                        WaitTimeSeconds=None, AttributeNames=None,
                        MessageAttributeNames=None, *args, **kwargs):
        assert isinstance(QueueUrl, str) and QueueUrl.strip() != ""
        if MaxNumberOfMessages:
            assert isinstance(MaxNumberOfMessages, int)
        if WaitTimeSeconds:
            assert isinstance(WaitTimeSeconds, int)
        if AttributeNames:
            assert isinstance(AttributeNames, list)
        if MessageAttributeNames:
            assert isinstance(MessageAttributeNames, list)
        return {"Messages":[{"MessageId":"mock_message_id1"},{"MessageId":"mock_message_id2"},{"MessageId":"mock_message_id3"}]}
    sqs.receive_message.side_effect = receive_message

    def delete_message(QueueUrl="", ReceiptHandle="", *args, **kwargs):
        assert isinstance(QueueUrl, str) and QueueUrl.strip() != ""
        assert isinstance(ReceiptHandle, str) and ReceiptHandle.strip() != ""
        return {"mock_key":"mock_value"}
    sqs.delete_message.side_effect = delete_message

    sts = _get_client("sts")
    def assume_role(RoleArn="", RoleSessionName="", *args, **kwargs):
        assert isinstance(RoleArn,str) and RoleArn.strip() != ""
        assert isinstance(RoleSessionName,str) and RoleSessionName.strip() != ""
        return {'Credentials': {
                'AccessKeyId': 'mock_access_key_id',
                'SecretAccessKey': 'mock_secret_access_key',
                'SessionToken': 'mock_session_token',
                'Expiration': datetime.now(tz=timezone.utc)+timedelta(hours=1)
            },
            'AssumedRoleUser': {
                'AssumedRoleId': 'mock_assume_role_id',
                'Arn': 'mock_arn'
            },
            'PackedPolicySize': 123,
            'SourceIdentity': 'mock_source_identity'
        }
    sts.assume_role.side_effect = assume_role

    ce = _get_client("ce")
    def get_cost_and_usage(TimePeriod={}, Granularity="", Metrics=[], Filter={}, *args, **kwargs):
        assert isinstance(TimePeriod, dict) 
        assert isinstance(TimePeriod.get("Start"), str) 
        assert isinstance(TimePeriod.get("End"), str) 
        assert Granularity == "MONTHLY" or Granularity == "DAILY" or Granularity == "HOURLY"
        assert isinstance(Metrics, list)
        metric_values = ["AmortizedCost", "BlendedCost", "NetAmortizedCost", "NetUnblendedCost", "NormalizedUsageAmount", "UnblendedCost", "UsageQuantity"]
        assert any(metric in Metrics for metric in metric_values)
        if Filter:
            assert isinstance(Filter, dict)
        start = datetime.strptime(TimePeriod["Start"], "%Y-%m-%d")
        end = datetime.strptime(TimePeriod["End"], "%Y-%m-%d")
        delta = timedelta(days=1)
        assert end - start == delta
        
        return {
            "ResultsByTime": [{
                "TimePeriod": {"Start": f"{start}", "End": f"{end}"},
                "Total": {"UnblendedCost": {"Amount": "100.0", "Unit": "USD"},
                        "NetUnblendedCost": {"Amount": "100.0", "Unit": "USD"},
                        "NetAmortizedCost": {"Amount": "100.0", "Unit": "USD"}}
            }]
        }
    ce.get_cost_and_usage.side_effect = get_cost_and_usage

    # Patch boto3.client globally
    monkeypatch.setattr(boto3, "client", _get_client)
    yield _get_client 