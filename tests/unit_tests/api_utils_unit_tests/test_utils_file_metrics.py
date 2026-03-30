import pytest
from datetime import datetime, timezone 
import uuid

from app.v2.utils.file_metrics import (get_daily_volume, get_daily_count, get_overall_volume,
                                       get_overall_count, get_status_counts, get_metrics_summary,
                                       get_summary_cost, get_cost_by_collection, get_cost_by_file)
from app.v2.type_util.file_metrics import MetricsQueryParameters

@pytest.mark.asyncio
async def test_get_daily_volume(make_request,  test_admin_user, test_ngroup_id, seed_file):
    """Test getting the daily volume metrics"""
    req = make_request()
    query_params = MetricsQueryParameters()
    upload_time = datetime.now(tz=timezone.utc)
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, upload_time=upload_time)
    daily_volume = await get_daily_volume(req, test_admin_user, str(test_ngroup_id), query_params)
    assert daily_volume[0]["value"] == 1075841024

@pytest.mark.asyncio
async def test_get_daily_count(make_request,  test_admin_user, test_ngroup_id, seed_file):
    """Test getting daily count metrics."""
    req = make_request()
    query_params = MetricsQueryParameters()
    upload_time = datetime.now(tz=timezone.utc)
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, upload_time=upload_time)

    daily_count = await get_daily_count(req, test_admin_user, str(test_ngroup_id), query_params)
    assert daily_count[0]["value"] == 5

@pytest.mark.asyncio
async def test_get_overall_volume(make_request,  test_admin_user, test_ngroup_id, seed_file):
    """Test getting the overall volume metric."""
    req = make_request()
    query_params = MetricsQueryParameters()
    upload_time = datetime.now(tz=timezone.utc)
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, upload_time=upload_time)
    overall_volume = await get_overall_volume(req, test_admin_user, str(test_ngroup_id), query_params)
    assert overall_volume["value"] == 1075841024

@pytest.mark.asyncio
async def test_get_overall_count(make_request,  test_admin_user, test_ngroup_id, seed_file):
    """Test getting the overall count metric."""
    req = make_request()
    query_params = MetricsQueryParameters()
    upload_time = datetime.now(tz=timezone.utc)
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file6", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file7", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, upload_time=upload_time)
    counts = await get_overall_count(req, test_admin_user, str(test_ngroup_id), query_params)
    assert counts["value"] == 7

@pytest.mark.asyncio
async def test_get_status_counts(make_request,  test_admin_user, test_ngroup_id, seed_file):
    """Test getting the status counts metrics"""
    req = make_request()
    query_params = MetricsQueryParameters()
    upload_time = datetime.now(tz=timezone.utc)
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, status="infected",upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024, status="scan_failed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file6", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="clean", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file7", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="unscanned", upload_time=upload_time)
    status_counts = await get_status_counts(req, test_admin_user, str(test_ngroup_id), query_params)
    assert {"status":"distributed", "count":3} in status_counts 
    assert {"status":"clean", "count":1} in status_counts 
    assert {"status":"scan_failed", "count":1} in status_counts 
    assert {"status":"infected", "count":1} in status_counts 
    assert {"status":"unscanned", "count":1} in status_counts 

@pytest.mark.asyncio
async def test_get_metrics_summary(make_request,  test_admin_user, test_ngroup_id, seed_file):
    """Test getting a metrics summary."""
    req = make_request()
    query_params = MetricsQueryParameters()
    upload_time = datetime.now(tz=timezone.utc)
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, status="infected",upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024, status="scan_failed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file6", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="clean", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file7", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="unscanned", upload_time=upload_time)
    summary = await get_metrics_summary(req, test_admin_user, str(test_ngroup_id), query_params)
    assert summary['daily_volume'][0]['value'] == 2149583872
    assert summary['daily_count'][0]['value'] == 7
    assert summary['overall_volume']['value'] == 2149583872
    assert summary['overall_count']['value'] == 7
    assert {"status":"distributed", "count":3} in summary['status_counts']
    assert {"status":"clean", "count":1} in summary['status_counts']
    assert {"status":"scan_failed", "count":1} in summary['status_counts']
    assert {"status":"infected", "count":1} in summary['status_counts']
    assert {"status":"unscanned", "count":1} in summary['status_counts']


#V1 style cost calculation logic
@pytest.mark.asyncio
async def test_get_summary_cost(make_request, test_admin_user, seed_file):
    """Test getting summary cost metrics"""
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, status="distributed")
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024, status="distributed")
    await seed_file(uuid.uuid4(), "file6", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="distributed")
    await seed_file(uuid.uuid4(), "file7", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="distributed")
    req = make_request()
    mock_query_params = MetricsQueryParameters()
    summary_cost = await get_summary_cost(req, test_admin_user, test_admin_user.ngroups[0], mock_query_params)
    assert summary_cost["total_files"] == 7
    assert summary_cost["total_cost"]["value"] == 0.03
    assert len(summary_cost["daily_cost"]) == 1


@pytest.mark.asyncio
async def test_get_cost_by_collection(make_request, test_admin_user, test_collection, seed_file):
    """Test getting cost by collection metrics"""
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, status="distributed")
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024, status="distributed")
    await seed_file(uuid.uuid4(), "file6", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="distributed")
    await seed_file(uuid.uuid4(), "file7", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="distributed")
    req = make_request()
    mock_query_params = MetricsQueryParameters()
    collection_cost = await get_cost_by_collection(req, test_admin_user, test_admin_user.ngroups[0], mock_query_params, 1, 15)
    assert collection_cost
    assert len(collection_cost[0]) == collection_cost[1]
    assert collection_cost[0][0]["name"] == test_collection["short_name"]

@pytest.mark.asyncio
async def test_get_cost_by_file(make_request, test_admin_user, seed_file):
    """Test getting cost by file metrics"""
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, status="distributed")
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024, status="distributed")
    await seed_file(uuid.uuid4(), "file6", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="distributed")
    await seed_file(uuid.uuid4(), "file7", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="distributed")
    req = make_request()
    mock_query_params = MetricsQueryParameters()
    file_cost = await get_cost_by_file(req, test_admin_user, test_admin_user.ngroups[0], mock_query_params, 1, 15)
    assert len(file_cost[0]) == file_cost[1]
