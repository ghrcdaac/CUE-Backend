import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
import asyncpg
import uuid
import json


from app.v2.utils.file_status import (create_file_status, get_file_status, update_file_status,
                                      delete_file_status, list_file_statuses, get_file_status_counts,
                                      calculate_daily_volume, calculate_daily_count, calculate_overall_volume,
                                      calculate_overall_count, list_files_by_status, get_metrics_summary,
                                      FileStatusNotFoundError, BYTES_TO_GB, AuthorizationError)
from app.v2.type_util.file_status import FileStatusCreate, FileStatusUpdate
from app.v2.type_util.file_metrics import MetricsQueryParameters

@pytest.mark.asyncio
async def test_create_file_status(connection_pool, test_collection, test_admin_user):
    """Test creating a file status"""
    file_id = uuid.uuid4()
    query = """INSERT INTO file
               (id, name, type, cueuser_uploaded, size_bytes, collection_id, checksum)
               VALUES ($1, $2, $3, $4, $5, $6, $7);"""
    params = (file_id, "test_file", "application/octet-stream",
              test_admin_user.id, 1024, test_collection["id"], "mock_checksum")
    async with connection_pool.acquire() as conn:
        await conn.execute(query, *params)
    mock_file_status = FileStatusCreate(id=file_id, status="clean", upload_time=datetime.now(tz=timezone.utc))
    file_status = await create_file_status(mock_file_status, uuid.UUID(test_admin_user.ngroups[0]))
    assert file_status.id == file_id
    assert file_status.status == "clean"

@pytest.mark.asyncio
async def test_create_file_status_file_not_found(test_admin_user):
    """Test creating a file status for file that does not exists"""
    file_id = uuid.uuid4()
    mock_file_status = FileStatusCreate(id=file_id, status="clean", upload_time=datetime.now(tz=timezone.utc))
    with pytest.raises(FileStatusNotFoundError):
         await create_file_status(mock_file_status, uuid.UUID(test_admin_user.ngroups[0]))

@pytest.mark.asyncio
async def test_create_file_status_not_authorized(connection_pool, test_collection, test_admin_user, seed_ngroup):
    """Test creating a file status in different ngroup"""
    file_id = uuid.uuid4()
    query = """INSERT INTO file
               (id, name, type, cueuser_uploaded, size_bytes, collection_id, checksum)
               VALUES ($1, $2, $3, $4, $5, $6, $7);"""
    params = (file_id, "test_file", "application/octet-stream",
              test_admin_user.id, 1024, test_collection["id"], "mock_checksum")
    async with connection_pool.acquire() as conn:
        await conn.execute(query, *params)

    ngroup_id2 = uuid.uuid4()
    await seed_ngroup(ngroup_id2, "test_ngroup2", "Test Ngroup 2")

    mock_file_status = FileStatusCreate(id=file_id, status="clean", upload_time=datetime.now(tz=timezone.utc))
    with pytest.raises(AuthorizationError):
        await create_file_status(mock_file_status, ngroup_id2)

@pytest.mark.asyncio
async def test_create_file_status_create_duplicate_status(seed_file, test_admin_user):
    """Test creating a duplicate file status."""
    file_id = uuid.uuid4()
    await seed_file(file_id, "test_file", "application/octet-stream", test_admin_user.id, 1024)

    mock_file_status = FileStatusCreate(id=file_id, status="clean", upload_time=datetime.now(tz=timezone.utc))
    with pytest.raises(ValueError):
        await create_file_status(mock_file_status, uuid.UUID(test_admin_user.ngroups[0]))

@pytest.mark.asyncio
async def test_get_file_status(seed_file, test_admin_user):
    """Test getting a file status."""
    file_id = uuid.uuid4()
    await seed_file(file_id, "file", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    file_status = await get_file_status(file_id)
    assert file_status.id == file_id
    assert file_status.status == "distributed"

@pytest.mark.asyncio
async def test_get_file_status_not_found():
    """Test getting a file status that does not exists."""
    file_id = uuid.uuid4()

    with pytest.raises(FileStatusNotFoundError):
        await get_file_status(file_id)

@pytest.mark.asyncio
async def test_update_file_status(seed_file, test_admin_user):
    """Test updating a file status."""
    file_id = uuid.uuid4()
    upload_time = datetime.now(tz=timezone.utc)
    scan_start = timedelta(microseconds=10) + datetime.now(tz=timezone.utc)
    scan_end = timedelta(microseconds=30) + datetime.now(tz=timezone.utc)
    egress_start = timedelta(microseconds=70) + datetime.now(tz=timezone.utc)

    await seed_file(file_id, "file", 'application/octet-stream',
                    test_admin_user.id, 1024, status="clean",
                    upload_time=upload_time, scan_start=scan_start, scan_end=scan_end,
                    scan_results=json.dumps({"mock_result":"mock_value"}))

    mock_file_status_update = FileStatusUpdate(status="distributed", egress_start=egress_start)
    file_status = await update_file_status(file_id, mock_file_status_update)
    assert file_status.status == "distributed"
    assert file_status.egress_start == egress_start

@pytest.mark.asyncio
async def test_update_file_status_file_does_not_exists():
    """Test updating a file status for file that does not exist"""
    file_id = uuid.uuid4()
    egress_start = timedelta(microseconds=70) + datetime.now(tz=timezone.utc)

    mock_file_status_update = FileStatusUpdate(status="distributed", egress_start=egress_start)
    with pytest.raises(FileStatusNotFoundError):
        await update_file_status(file_id, mock_file_status_update)

@pytest.mark.asyncio
async def test_delete_file_status(seed_file, test_admin_user):
    """Test deleting a file status."""
    file_id = uuid.uuid4()
    await seed_file(file_id, "file", 'application/octet-stream', test_admin_user.id, 1024, status="unscanned")
    success = await delete_file_status(file_id)
    assert success

@pytest.mark.asyncio
async def test_delete_file_status_not_found():
    """Test deleting a file status that does not exists."""
    file_id = uuid.uuid4()
    with pytest.raises(FileStatusNotFoundError):
        await delete_file_status(file_id)

@pytest.mark.asyncio
async def test_get_file_status_counts(test_admin_user, test_ngroup_id,  seed_file):
    """Test getting file status counts"""
    query_params = MetricsQueryParameters()
    upload_time = datetime.now(tz=timezone.utc)
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, status="infected",upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024, status="scan_failed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file6", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="clean", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file7", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="unscanned", upload_time=upload_time)
    status_counts = await get_file_status_counts(test_ngroup_id, query_params) 
    assert status_counts["distributed"] == 3 
    assert status_counts["clean"] == 1 
    assert status_counts["scan_failed"] == 1
    assert status_counts["infected"] == 1
    assert status_counts["unscanned"] == 1

@pytest.mark.asyncio
async def test_calculate_daily_volume( test_admin_user, test_ngroup_id, seed_file):
    """Test calculating daily volume."""
    query_params = MetricsQueryParameters()
    upload_time = datetime.now(tz=timezone.utc)
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    daily_volume = await calculate_daily_volume(test_ngroup_id, query_params)
    assert daily_volume[0].value == float(3147776*BYTES_TO_GB)

@pytest.mark.asyncio
async def test_calculate_daily_count( seed_file, test_admin_user, test_ngroup_id):
    """Test calculating daily count."""
    query_params = MetricsQueryParameters()
    upload_time = datetime.now(tz=timezone.utc)
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, upload_time=upload_time)

    daily_count = await calculate_daily_count(test_ngroup_id, query_params)
    assert daily_count[0].value == 5.0

@pytest.mark.asyncio
async def test_calculate_overall_volume( seed_file, test_admin_user, test_ngroup_id):
    """Test calculate overall volume."""
    query_params = MetricsQueryParameters()
    upload_time = datetime.now(tz=timezone.utc)
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, upload_time=upload_time)
    overall_volume = await calculate_overall_volume(test_ngroup_id, query_params)
    assert overall_volume.value == float(1075841024*BYTES_TO_GB)

@pytest.mark.asyncio
async def test_calculate_overall_count( seed_file, test_admin_user, test_ngroup_id):
    """Test calculating overall count."""
    query_params = MetricsQueryParameters()
    upload_time = datetime.now(tz=timezone.utc)
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file6", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file7", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, upload_time=upload_time)
    counts = await calculate_overall_count(test_ngroup_id, query_params)
    assert counts.value == 7

@pytest.mark.asyncio
async def test_list_files_by_status(seed_file, test_ngroup_id, test_admin_user):
    query_params = MetricsQueryParameters()
    upload_time = datetime.now(tz=timezone.utc)
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, status="infected",upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024, status="scan_failed", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file6", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="clean", upload_time=upload_time)
    await seed_file(uuid.uuid4(), "file7", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="unscanned", upload_time=upload_time)
    status_list = await list_files_by_status(test_ngroup_id, "distributed", query_params, 1, 15)
    assert isinstance(status_list, tuple)
    assert status_list[1] == 3

    status_list = await list_files_by_status(test_ngroup_id, "infected", query_params, 1, 15)
    assert status_list[1] == 1

    status_list = await list_files_by_status(test_ngroup_id, "scan_failed", query_params, 1, 15)
    assert status_list[1] == 1

    status_list = await list_files_by_status(test_ngroup_id, "clean", query_params, 1, 15)
    assert status_list[1] == 1

    status_list = await list_files_by_status(test_ngroup_id, "unscanned", query_params, 1, 15)
    assert status_list[1] == 1

@pytest.mark.asyncio
async def test_list_files_by_status_invalid_status(test_ngroup_id):
    query_params = MetricsQueryParameters()
    with pytest.raises(ValueError):
        await list_files_by_status(test_ngroup_id, "invalid_status", query_params, 1, 15)

@pytest.mark.asyncio
async def test_list_file_statuses(seed_file, test_ngroup_id, test_admin_user):
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, status="infected")
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024, status="scan_failed")
    await seed_file(uuid.uuid4(), "file6", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="clean")
    await seed_file(uuid.uuid4(), "file7", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="unscanned")
    statuses = await list_file_statuses(test_ngroup_id)
    assert isinstance(statuses,list)

@pytest.mark.asyncio
async def test_get_metrics_summary( seed_file, test_ngroup_id, test_admin_user):
    query_params = MetricsQueryParameters()
    upload_time1 = datetime.now(tz=timezone.utc)
    upload_time2 = upload_time1 - timedelta(days=1)
    await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time1)
    await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time1)
    await seed_file(uuid.uuid4(), "file3", 'application/octet-stream', test_admin_user.id, 1024, status="distributed", upload_time=upload_time2)
    await seed_file(uuid.uuid4(), "file4", 'application/octet-stream', test_admin_user.id, 1024*1024, status="infected",upload_time=upload_time2)
    await seed_file(uuid.uuid4(), "file5", 'application/octet-stream', test_admin_user.id, 1024*1024, status="scan_failed", upload_time=upload_time1)
    await seed_file(uuid.uuid4(), "file6", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="clean", upload_time=upload_time2)
    await seed_file(uuid.uuid4(), "file7", 'application/octet-stream', test_admin_user.id, 1024*1024*1024, status="unscanned", upload_time=upload_time1)
    summary = await get_metrics_summary(test_ngroup_id, query_params)
    assert sum([day.value for day in summary.daily_volume]) == float(2149583872*BYTES_TO_GB)
    assert sum([day.value for day in summary.daily_count]) == 7
    assert summary.overall_volume.value == float(2149583872*BYTES_TO_GB)
    assert summary.overall_count.value == 7
    assert summary.status_counts["distributed"]== 3
    assert summary.status_counts["clean"] == 1
    assert summary.status_counts["scan_failed"] == 1
    assert summary.status_counts["infected"] == 1
    assert summary.status_counts["unscanned"] == 1 