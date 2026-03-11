import pytest
import uuid
from botocore.exceptions import ClientError

@pytest.mark.asyncio
async def test_start_query_endpoint(test_client, test_admin_user, seed_test_files, mock_boto3_client, make_jwt):
    """Test start query endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}
    await seed_test_files(test_admin_user.id, upload_offset=90)
    body = {}

    response = test_client.post("/v2/archive/queries", headers=headers, json=body)
    response_json = response.json()
    assert response.status_code == 202
    assert response_json.get("query_execution_id")

@pytest.mark.asyncio
async def test_start_query_endpoint_no_files(test_client, test_admin_user, mock_boto3_client, make_jwt):
    """Test start query endpoint - No archived records."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}
    body = {}

    response = test_client.post("/v2/archive/queries", headers=headers, json=body)
    response_json = response.json()    
    assert response.status_code == 404 
    assert response_json.get("detail") == "No archived records match the specified filters."

@pytest.mark.asyncio
async def test_get_query_status_endpoint(test_client, test_admin_user, seed_test_files, mock_boto3_client, make_jwt):
    """Test get query status endpoint - success."""
    athena = mock_boto3_client("athena")
    athena.get_query_execution.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"get_query_execution.failed"}}, operation_name="get_query_execution")
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}
    await seed_test_files(test_admin_user.id, upload_offset=90)
    query_execution_id = uuid.uuid4()
    response = test_client.get(f"/v2/archive/queries/{query_execution_id}/status", headers=headers) 
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_get_query_results_endpoint(test_client, test_admin_user, seed_test_files, mock_boto3_client, make_jwt):
    """Test get query results endpoint - success."""
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}
    await seed_test_files(test_admin_user.id, upload_offset=90)
    query_execution_id = uuid.uuid4()
    response = test_client.get(f"/v2/archive/queries/{query_execution_id}/results", headers=headers) 
    assert response.status_code == 200


