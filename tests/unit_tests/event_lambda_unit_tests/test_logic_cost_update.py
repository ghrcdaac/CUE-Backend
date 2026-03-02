import pytest
import uuid
from app.event_lambdas.cost_update.logic import get_css_creds, get_scan_cost, get_aws_cost, calculate_cost_per_file, get_scan_cost, get_aws_cost, update_file_costs, CostUpdateError
from botocore.exceptions import ClientError
from unittest.mock import patch
from decimal import Decimal
from datetime import datetime, timezone, timedelta

@pytest.mark.asyncio
async def test_get_css_creds(mock_boto3_client):
    credentials = await get_css_creds()
    assert credentials.get("AccessKeyId")
    assert credentials.get("SecretAccessKey")
    assert credentials.get("SessionToken")

@pytest.mark.asyncio
async def test_get_css_creds_clienterror_fail(mock_boto3_client):
    sts = mock_boto3_client("sts")
    sts.assume_role.side_effect =  ClientError({"Error":{"Message":"Forced Error", "Code":"assume_role.failed"}}, operation_name="assume_role") 
    with pytest.raises(CostUpdateError):
        await get_css_creds()

@pytest.mark.asyncio
async def test_get_css_creds_unexpected_error_fail(mock_boto3_client):
    sts = mock_boto3_client("sts")
    sts.assume_role.side_effect = Exception("Forced Unexpected Error") 
    with pytest.raises(CostUpdateError):
        await get_css_creds()

@pytest.mark.asyncio
async def test_get_scan_cost(mock_boto3_client):
    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=1)
    cost = await get_scan_cost(start_time, end_time)
    assert cost["UnblendedCost"] == 100
    assert cost["NetUnblendedCost"] == 100
    assert cost["NetAmortizedCost"] == 100

@pytest.mark.asyncio
async def test_get_scan_cost_get_cost_usage_clienterror_fail(mock_boto3_client):
    ce = mock_boto3_client("ce")
    ce.get_cost_and_usage.side_effect =  ClientError({"Error":{"Message":"Forced Error", "Code":"get_cost_and_usage.failed"}}, operation_name="get_cost_and_usage") 
    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=1)
    with pytest.raises(CostUpdateError):
        await get_scan_cost(start_time, end_time)

@pytest.mark.asyncio
async def test_get_scan_cost_get_cost_usage_unexpected_fail(mock_boto3_client):
    ce = mock_boto3_client("ce")
    ce.get_cost_and_usage.side_effect = Exception("Forced Unexpected Error")
    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=1)
    with pytest.raises(CostUpdateError):
        await get_scan_cost(start_time, end_time)

@pytest.mark.asyncio
async def test_get_aws_cost(mock_boto3_client):
    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=1)
    cost = await get_aws_cost(start_time, end_time)
    assert cost["UnblendedCost"] == 100
    assert cost["NetUnblendedCost"] == 100
    assert cost["NetAmortizedCost"] == 100

@pytest.mark.asyncio
async def test_get_aws_cost_get_cost_and_usage_clienterror_fail(mock_boto3_client):
    ce = mock_boto3_client("ce")
    ce.get_cost_and_usage.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"get_cost_and_usage.failed"}}, operation_name="get_cost_and_usage") 
    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=1)
    with pytest.raises(CostUpdateError):
        await get_aws_cost(start_time, end_time)

@pytest.mark.asyncio
async def test_get_aws_cost_get_cost_and_usage_unexpected_error_fail(mock_boto3_client):
    ce = mock_boto3_client("ce")
    ce.get_cost_and_usage.side_effect = Exception("Forced Unexpected Error") 
    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=1)
    with pytest.raises(CostUpdateError):
        await get_aws_cost(start_time, end_time)

@pytest.mark.asyncio
async def test_calculate_cost_per_file(mock_boto3_client, seed_file, test_admin_user):
    file_id1 = uuid.uuid4()
    file_id2 = uuid.uuid4()
    
    file1 = await seed_file(file_id1, "file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
    file2 = await seed_file(file_id2, "file2", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")

    files = [{"file_id":file_id1, "file_size":file1["file"]["size_bytes"]},{"file_id":file_id2, "file_size":file2["file"]["size_bytes"]}]
    total_size = file1["file"]["size_bytes"] + file2["file"]["size_bytes"]

    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=1)

    scan_cost = await get_scan_cost(start_time, end_time)
    scan_cost_per_byte = {
        "UnblendedCost": scan_cost["UnblendedCost"] / total_size if scan_cost["UnblendedCost"] > 0.0 else Decimal(0.0),
        "NetUnblendedCost": scan_cost["NetUnblendedCost"] / total_size if scan_cost["NetUnblendedCost"] > 0.0 else Decimal(0.0)
    }
    scan_file_costs = await calculate_cost_per_file(files, "scan", scan_cost_per_byte)
    assert (file_id1, '{"type": "scan", "unblended_cost": 50.0, "net_unblended_cost": 50.0}') in scan_file_costs
    assert (file_id2, '{"type": "scan", "unblended_cost": 50.0, "net_unblended_cost": 50.0}') in scan_file_costs

    aws_cost = await get_aws_cost(start_time, end_time)
    aws_cost_per_byte = {
        "UnblendedCost": scan_cost["UnblendedCost"] / total_size if aws_cost["UnblendedCost"] > 0.0 else Decimal(0.0),
        "NetUnblendedCost": scan_cost["NetUnblendedCost"] / total_size if aws_cost["NetUnblendedCost"] > 0.0 else Decimal(0.0)
    }
    aws_file_costs = await calculate_cost_per_file(files, "aws", aws_cost_per_byte)

    assert (file_id1, '{"type": "aws", "unblended_cost": 50.0, "net_unblended_cost": 50.0}') in aws_file_costs
    assert (file_id2, '{"type": "aws", "unblended_cost": 50.0, "net_unblended_cost": 50.0}') in aws_file_costs

@pytest.mark.asyncio
async def test_update_file_costs(mock_boto3_client, seed_file, test_admin_user, connection_pool):

    file_id1 = uuid.uuid4()
    file_id2 = uuid.uuid4()

    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=1)
    upload_time = start_time + timedelta(hours=1)
    await seed_file(file_id1, "file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time, scan_results='[]')
    await seed_file(file_id2, "file2", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time, scan_results='[]')
    

    await update_file_costs(start_time, end_time, connection_pool)
    async with connection_pool.acquire() as conn:
        results = await conn.fetch("SELECT id, scan_results FROM file_status WHERE id = ANY($1::uuid[])", [file_id1, file_id2])

    results_list = [(record["id"],record["scan_results"]) for record in results]
    expected_scan_result = '[{"type": "scan", "unblended_cost": 50.0, "net_unblended_cost": 50.0}, {"type": "aws", "unblended_cost": 50.0, "net_unblended_cost": 50.0}]' 

    assert (file_id1, expected_scan_result) in results_list
    assert (file_id2, expected_scan_result) in results_list

@pytest.mark.asyncio
async def test_update_file_costs_fail(mock_boto3_client, connection_pool):
    ce = mock_boto3_client("ce")
    ce.get_cost_and_usage.side_effect = Exception("Forced Unexpected Error") 

    end_time = datetime.now(tz=timezone.utc)
    start_time = end_time - timedelta(days=1)
    with pytest.raises(CostUpdateError):
        await update_file_costs(start_time, end_time, connection_pool)