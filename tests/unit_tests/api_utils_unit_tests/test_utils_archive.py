import pytest
import uuid
from botocore.exceptions import ClientError
from app.v2.utils.archive import start_archive_query, get_query_status, get_query_results, AthenaError
from app.v2.type_util.file_metrics import MetricsQueryParameters
import os

@pytest.mark.asyncio
async def test_start_archive_query(test_ngroup_id, seed_file, test_admin_user, mock_boto3_client):
    """Test starting an archive query."""
    await seed_file(uuid.uuid4(), "file", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    mock_params = MetricsQueryParameters()
    query_id = await start_archive_query(test_ngroup_id, mock_params)
    assert query_id

@pytest.mark.asyncio
async def test_start_archive_query_clienterror(test_ngroup_id, seed_file, test_admin_user, mock_boto3_client):
    """Test starting an archive, but ClientError occurs."""
    athena = mock_boto3_client("athena")
    athena.start_query_execution.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"start_query_execution.failed"}}, operation_name="start_query_execution")
    await seed_file(uuid.uuid4(), "file", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    mock_params = MetricsQueryParameters()
    with pytest.raises(AthenaError):
        await start_archive_query(test_ngroup_id, mock_params)

@pytest.mark.asyncio
async def test_get_query_status(test_ngroup_id,  seed_file, test_admin_user, mock_boto3_client):
    """Test getting query status on archive query."""
    await seed_file(uuid.uuid4(), "file", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    mock_params = MetricsQueryParameters()
    query_id = await start_archive_query(test_ngroup_id, mock_params)
    result = await get_query_status(query_id)
    assert result  

@pytest.mark.asyncio
async def test_get_query_status_clienterror(test_ngroup_id,  seed_file, test_admin_user, mock_boto3_client):
    """Test getting query status on archive query, but ClientError occurs."""
    athena = mock_boto3_client("athena")
    athena.get_query_execution.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"get_query_execution.failed"}}, operation_name="get_query_execution")
    await seed_file(uuid.uuid4(), "file", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    mock_params = MetricsQueryParameters()
    query_id = await start_archive_query(test_ngroup_id, mock_params)
    with pytest.raises(AthenaError):
        await get_query_status(query_id)

@pytest.mark.asyncio
async def test_get_query_results(test_ngroup_id,  seed_file, test_admin_user, mock_boto3_client):
    """Test getting query results from archive query."""
    await seed_file(uuid.uuid4(), "file", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    mock_params = MetricsQueryParameters()
    query_id = await start_archive_query(test_ngroup_id, mock_params)
    result = await get_query_results(query_id)
    assert result
    
@pytest.mark.asyncio
async def test_get_query_results_clienterror(test_ngroup_id,  seed_file, test_admin_user, mock_boto3_client):
    """Test getting query results from archive query, but ClientError occurs."""
    s3 = mock_boto3_client("s3")
    s3.get_object.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"get_object.failed"}}, operation_name="get_object")
    await seed_file(uuid.uuid4(), "file", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    mock_params = MetricsQueryParameters()
    query_id = await start_archive_query(test_ngroup_id, mock_params)
    with pytest.raises(AthenaError):
        await get_query_results(query_id)