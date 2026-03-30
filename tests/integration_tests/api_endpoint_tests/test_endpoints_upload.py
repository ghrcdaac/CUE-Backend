
import uuid
from app.v2.type_util.api_keys import ApiKeyCreateResponse
from app.v2.type_util.upload import PartInfo
from botocore.exceptions import ClientError


def test_prepare_single_upload_endpoint(test_client, test_admin_user, test_ngroup_id, test_collection, make_jwt, mock_boto3_client):
    """Test prepare single upload endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    api_key_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key = get_api_key(test_client, api_key_headers, test_ngroup_id)
    upload_headers = {"Authorization": f"Bearer {api_key["key"]}"}
    prepare_upload_request = {"collection_name": test_collection["short_name"],
                              "file_name": "test_upload",
                              "file_size_bytes": 1024,
                              "collection_path": "",
                              "checksum":"mock_checksum",
                              "content_type": "application/octet-stream"}
    

    response = test_client.post("/v2/upload/prepare-single", headers=upload_headers, json=prepare_upload_request)
    response_json = response.json()
    assert response.status_code == 200
    assert isinstance(uuid.UUID(response_json["file_id"]), uuid.UUID)
    assert response_json["presigned_url"] == "http://localhost/mock_presigned_url"
   
def test_prepare_single_upload_endpoint_client_error(test_client, test_admin_user, test_ngroup_id, test_collection, make_jwt, mock_boto3_client):
    """Test prepare single upload endpoint - s3 client fails to generate presigned url."""
    s3 = mock_boto3_client("s3")
    s3.generate_presigned_url.side_effect=ClientError({"Error":{"Message":"Forced Error", "Code":"generate_presigned_url.failed"}}, 
                                                       operation_name="generate_presigned_url")

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    api_key_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key = get_api_key(test_client, api_key_headers, test_ngroup_id)
    upload_headers = {"Authorization": f"Bearer {api_key["key"]}"}
    prepare_upload_request = {"collection_name": test_collection["short_name"],
                              "file_name": "test_upload",
                              "file_size_bytes": 1024,
                              "collection_path": "",
                              "checksum":"mock_checksum",
                              "content_type": "application/octet-stream"}
    

    response = test_client.post("/v2/upload/prepare-single", headers=upload_headers, json=prepare_upload_request)
    assert response.status_code == 503

def test_prepare_single_upload_endpoint_collection_not_found(test_client, test_admin_user, test_ngroup_id, make_jwt, mock_boto3_client):
    """Test prepare single upload endpoint - collection does not exist."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    api_key_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key = get_api_key(test_client, api_key_headers, test_ngroup_id)
    upload_headers = {"Authorization": f"Bearer {api_key["key"]}"}
    prepare_upload_request = {"collection_name": "bad_name",
                              "file_name": "test_upload",
                              "file_size_bytes": 1024,
                              "collection_path": "",
                              "checksum":"mock_checksum",
                              "content_type": "application/octet-stream"}
    

    response = test_client.post("/v2/upload/prepare-single", headers=upload_headers, json=prepare_upload_request)
    assert response.status_code == 400
    
def test_complete_single_upload_endpoint(test_client, test_admin_user, test_ngroup_id, make_jwt, mock_boto3_client):
    """Test complete single upload endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    api_key_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key = get_api_key(test_client, api_key_headers, test_ngroup_id)
    upload_headers = {"Authorization": f"Bearer {api_key["key"]}"}
    file_id = uuid.uuid4()
    complete_upload_request = {"file_id": str(file_id),
                              "s3_etag":"mock_s3_etag"}
    response = test_client.post("/v2/upload/complete-single", headers=upload_headers, json=complete_upload_request)
    response_json = response.json()
    assert response.status_code == 200
    assert response_json["file_id"] == str(file_id)

def test_multipart_start_endpoint(test_client, test_admin_user, test_ngroup_id, test_collection, make_jwt, mock_boto3_client):
    """Test multipart start endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    api_key_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key = get_api_key(test_client, api_key_headers, test_ngroup_id)
    upload_headers = {"Authorization": f"Bearer {api_key["key"]}"}
    multi_start_request = {"collection_name": test_collection["short_name"],
                              "file_name": "test_upload",
                              "final_size_bytes": 1024*1024*1024,
                              "collection_path": "",
                              "checksum":"mock_checksum",
                              "content_type": "application/octet-stream"}
    response = test_client.post("/v2/upload/multipart/start", headers=upload_headers, json=multi_start_request)
    response_json = response.json()
    assert response.status_code == 200
    assert isinstance(uuid.UUID(response_json["file_id"]), uuid.UUID)
    assert response_json["upload_id"] != "" and response_json["upload_id"] is not None

def test_multipart_start_endpoint_collection_not_found(test_client, test_admin_user, test_ngroup_id, make_jwt, mock_boto3_client):
    """Test multipart start endpoint - collection does not exist."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    api_key_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key = get_api_key(test_client, api_key_headers, test_ngroup_id)
    upload_headers = {"Authorization": f"Bearer {api_key["key"]}"}
    multi_start_request = {"collection_name": "bad_name",
                              "file_name": "test_upload",
                              "final_size_bytes": 1024*1024*1024,
                              "collection_path": "",
                              "checksum":"mock_checksum",
                              "content_type": "application/octet-stream"}
    response = test_client.post("/v2/upload/multipart/start", headers=upload_headers, json=multi_start_request)
    assert response.status_code == 400

def test_multipart_start_endpoint_client_error(test_client, test_admin_user, test_ngroup_id, test_collection, make_jwt, mock_boto3_client):
    """Test multipart start endpoint - s3 client fails to create multipart upload."""
    s3 = mock_boto3_client("s3")
    s3.create_multipart_upload.side_effect=ClientError({"Error":{"Message":"Forced Error", "Code":"create_multipart_upload.failed"}},
                                                       operation_name="create_multipart_upload")

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    api_key_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key = get_api_key(test_client, api_key_headers, test_ngroup_id)
    upload_headers = {"Authorization": f"Bearer {api_key["key"]}"}
    multi_start_request = {"collection_name": test_collection["short_name"],
                              "file_name": "test_upload",
                              "final_size_bytes": 1024*1024*1024,
                              "collection_path": "",
                              "checksum":"mock_checksum",
                              "content_type": "application/octet-stream"}
    response = test_client.post("/v2/upload/multipart/start", headers=upload_headers, json=multi_start_request)
    assert response.status_code == 400

def test_multipart_get_part_url_endpoint(test_client, test_admin_user, test_ngroup_id, make_jwt, mock_boto3_client):
    """Test multipart get part url endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    api_key_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key = get_api_key(test_client, api_key_headers, test_ngroup_id)
    upload_headers = {"Authorization": f"Bearer {api_key["key"]}"}
    file_id = uuid.uuid4()
    multipart_get_part_url_request = {"file_id":str(file_id),
                           "upload_id": "mock_upload_id",
                           "part_number": 1}
    response = test_client.post("v2/upload/multipart/get-part-url", headers=upload_headers, json=multipart_get_part_url_request)
    response_json = response.json()
    assert response_json["presigned_url"] == "http://localhost/mock_presigned_url"

def test_multipart_get_part_url_endpoint_client_error(test_client, test_admin_user, test_ngroup_id, make_jwt, mock_boto3_client):
    """Test multipart get part url endpoint - s3 client fails to generate presigned url."""
    s3 = mock_boto3_client("s3")
    s3.generate_presigned_url.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"generate_presigned_url.failed"}}, 
                                                         operation_name="generate_presigned_url")

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    api_key_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key = get_api_key(test_client, api_key_headers, test_ngroup_id)
    upload_headers = {"Authorization": f"Bearer {api_key["key"]}"}
    file_id = uuid.uuid4()
    multipart_get_part_url_request = {"file_id":str(file_id),
                           "upload_id": "mock_upload_id",
                           "part_number": 1}
    response = test_client.post("v2/upload/multipart/get-part-url", headers=upload_headers, json=multipart_get_part_url_request)
    assert response.status_code == 500

def test_multipart_complete_endpoint(test_client, test_admin_user, test_ngroup_id, test_collection, make_jwt, mock_boto3_client):
    """Test multipart complete endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    api_key_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key = get_api_key(test_client, api_key_headers, test_ngroup_id)
    upload_headers = {"Authorization": f"Bearer {api_key["key"]}"}
    file_id = uuid.uuid4()
    multipart_complete_request = {
        "file_id": str(file_id),
        "upload_id": "mock_upload_id",
        "parts": [{"PartNumber":1, "ETag":"mock_etag1"}, {"PartNumber":2, "ETag":"mock_etag2"}, {"PartNumber":3, "ETag":"mock_etag3"}],
        "file_name": "test_upload",
        "collection_name": test_collection["short_name"],
        "collection_path":"",
        "content_type": "application/octet-stream",
        "checksum": "mock_checksum",
        "final_file_size": 1024*1024*1024
    }
    response = test_client.post("/v2/upload/multipart/complete", headers=upload_headers, json=multipart_complete_request)
    response_json = response.json()
    assert response.status_code == 200
    assert response_json["file_id"] == str(file_id)

def test_multipart_complete_endpoint_collection_not_found(test_client, test_admin_user, test_ngroup_id, test_collection, make_jwt, mock_boto3_client):
    """Test multipart complete endpoint - collection does not exist."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    api_key_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key = get_api_key(test_client, api_key_headers, test_ngroup_id)
    upload_headers = {"Authorization": f"Bearer {api_key["key"]}"}
    file_id = uuid.uuid4()
    multipart_complete_request = {
        "file_id": str(file_id),
        "upload_id": "mock_upload_id",
        "parts": [{"PartNumber":1, "ETag":"mock_etag1"}, {"PartNumber":2, "ETag":"mock_etag2"}, {"PartNumber":3, "ETag":"mock_etag3"}],
        "file_name": "test_upload",
        "collection_name": "bad_name",
        "collection_path":"",
        "content_type": "application/octet-stream",
        "checksum": "mock_checksum",
        "final_file_size": 1024*1024*1024
    }
    response = test_client.post("/v2/upload/multipart/complete", headers=upload_headers, json=multipart_complete_request)
    assert response.status_code == 400

def test_multipart_complete_endpoint_client_error(test_client, test_admin_user, test_ngroup_id, test_collection, make_jwt, mock_boto3_client):
    """Test multipart complete endpoint - s3 client fails to complete multipart upload."""
    s3 = mock_boto3_client("s3")
    s3.complete_multipart_upload.side_effect=ClientError({"Error":{"Message":"Forced Error", "Code":"complete_multipart_upload.failed"}},
                                                         operation_name="complete_multipart_upload")

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    api_key_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key = get_api_key(test_client, api_key_headers, test_ngroup_id)
    upload_headers = {"Authorization": f"Bearer {api_key["key"]}"}
    file_id = uuid.uuid4()
    multipart_complete_request = {
        "file_id": str(file_id),
        "upload_id": "mock_upload_id",
        "parts": [{"PartNumber":1, "ETag":"mock_etag1"}, {"PartNumber":2, "ETag":"mock_etag2"}, {"PartNumber":3, "ETag":"mock_etag3"}],
        "file_name": "test_upload",
        "collection_name": test_collection["short_name"],
        "collection_path":"",
        "content_type": "application/octet-stream",
        "checksum": "mock_checksum",
        "final_file_size": 1024*1024*1024
    }
    response = test_client.post("/v2/upload/multipart/complete", headers=upload_headers, json=multipart_complete_request)
    assert response.status_code == 400

def test_multipart_abort_endpoint(test_client, test_admin_user, test_ngroup_id, make_jwt, mock_boto3_client):
    """Test multipart abort endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    api_key_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key = get_api_key(test_client, api_key_headers, test_ngroup_id)
    upload_headers = {"Authorization": f"Bearer {api_key["key"]}"}
    file_id = uuid.uuid4()
    multipart_abort_request = {"file_id": str(file_id), "upload_id": "mock_upload_id"}
    response = test_client.post("/v2/upload/multipart/abort", headers=upload_headers, json=multipart_abort_request)
    assert response.status_code == 204

def test_multipart_abort_endpoint_client_error(test_client, test_admin_user, test_ngroup_id, make_jwt, mock_boto3_client):
    """Test multipart abort endpoint - s3 client fails to abort multipart upload."""
    s3 = mock_boto3_client("s3")
    s3.abort_multipart_upload.side_effect=ClientError({"Error":{"Message":"Forced Error", "Code":"abort_multipart_upload.failed"}},
                                                      operation_name="abort_multipart_upload")

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    api_key_headers = {"Authorization": f"Bearer {test_admin_user_jwt}"}
    api_key = get_api_key(test_client, api_key_headers, test_ngroup_id)
    upload_headers = {"Authorization": f"Bearer {api_key["key"]}"}
    file_id = uuid.uuid4()
    multipart_abort_request = {"file_id": str(file_id), "upload_id": "mock_upload_id"}
    response = test_client.post("/v2/upload/multipart/abort", headers=upload_headers, json=multipart_abort_request)
    assert response.status_code == 500



def get_api_key(test_client, headers:dict, ngroup_id:str, scopes=["file:upload"]) -> ApiKeyCreateResponse:
    """Helper function to create api keys"""
    api_key_create_request= {"name": "test_key",
                             "key_type": "personal",
                             "scopes": scopes,
                             "expires_in_days": 10,
                             "ngroup_id": str(ngroup_id)}
    response = test_client.post("v2/api-keys/", headers=headers, json=api_key_create_request)
    return response.json()