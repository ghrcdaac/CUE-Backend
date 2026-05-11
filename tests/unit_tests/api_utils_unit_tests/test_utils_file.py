import pytest
import pytest_asyncio
from typing import Tuple, Dict
from unittest.mock import patch, MagicMock
import uuid
import os

from app.v2.utils.file import (FileNotFoundError, InvalidApiKeyError, ApiKeyScopeError,
                               ApiKeyConfigurationError, FileAccessError, get_file_details,
                               find_files_by_name, search_files_by_name, list_files,
                               list_files_by_api_key, update_file, delete_file)
from app.v2.utils.api_keys import create_api_key
from app.v2.type_util.file import FileUpdateRequest, FileListRequest 
from app.v2.type_util.api_keys import ApiKeyCreateRequest

@pytest.mark.asyncio
async def test_get_file_details(make_request, seed_file, test_admin_user):
    """Test getting a file's details."""
    req = make_request()
    file_id = uuid.uuid4()
    mock_file = await seed_file(file_id, "file", "application/octet-stream",
                                test_admin_user.id, 1024, scan_results='{"mock_value":"mock_key"}')
    file_details = await get_file_details(req, mock_file["file"]["id"])

    assert mock_file["file"]["id"] == file_details["id"]
    assert mock_file["file"]["name"] == file_details["name"]

@pytest.mark.asyncio
async def test_get_file_details_not_found(make_request, seed_file, test_admin_user):
    """Test getting a file details but file does not exist."""
    req = make_request()
    file_id = uuid.uuid4()
    with pytest.raises(FileNotFoundError):
        await get_file_details(req, file_id)


@pytest.mark.asyncio
async def test_find_files_by_name(make_request, seed_file, test_admin_user):
    """Test getting a file by name."""
    req = make_request()
    file_id=uuid.uuid4()
    mock_file = await seed_file(file_id, "file", 'application/octet-stream', test_admin_user.id, 1024)
    file = await find_files_by_name(req, test_admin_user, None, mock_file["file"]["name"])
    assert file_id == file[0]["id"]
    assert mock_file["file"]["name"] == file[0]["name"]

@pytest.mark.asyncio
async def test_search_files_by_name(make_request, seed_file, test_admin_user):
    """Test searching files by partial name."""
    req = make_request()
    file_id1 = uuid.uuid4()
    file_id2 = uuid.uuid4()
    file_id3 = uuid.uuid4()
    await seed_file(file_id1, "granule-alpha.nc", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(file_id2, "granule-beta.nc", 'application/octet-stream', test_admin_user.id, 1024, status="clean")
    await seed_file(file_id3, "metadata.json", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")

    files, has_more = await search_files_by_name(req, test_admin_user, None, "gran", 1, 15)

    assert has_more is False
    assert {file_id1, file_id2} == {f["id"] for f in files}
    assert file_id3 not in [f["id"] for f in files]
    assert all(file["collection"]["id"] == file["collection_id"] for file in files)
    assert all(file["collection"]["name"] for file in files)

@pytest.mark.asyncio
async def test_search_files_by_name_has_more(make_request, seed_file, test_admin_user):
    """Test searching files fetches one extra row to detect more results."""
    req = make_request()
    file_id1 = uuid.uuid4()
    file_id2 = uuid.uuid4()
    await seed_file(file_id1, "granule-alpha.nc", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(file_id2, "granule-beta.nc", 'application/octet-stream', test_admin_user.id, 1024, status="clean")

    files, has_more = await search_files_by_name(req, test_admin_user, None, "granule", 1, 1)

    assert len(files) == 1
    assert has_more is True

@pytest.mark.asyncio
async def test_search_files_by_name_with_status(make_request, seed_file, test_admin_user):
    """Test searching files by partial name and status."""
    req = make_request()
    distributed_file_id = uuid.uuid4()
    clean_file_id = uuid.uuid4()
    await seed_file(distributed_file_id, "granule-alpha.nc", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_file(clean_file_id, "granule-beta.nc", 'application/octet-stream', test_admin_user.id, 1024, status="clean")

    files, has_more = await search_files_by_name(req, test_admin_user, None, "granule", 1, 15, "distributed")

    assert has_more is False
    assert files[0]["id"] == distributed_file_id

@pytest.mark.asyncio
async def test_list_files(make_request, seed_file, test_admin_user):
    """Test getting a list of files"""
    req = make_request()
    file_id1 = uuid.uuid4()
    file_id2 = uuid.uuid4()
    mock_file1 = await seed_file(file_id1, "file1", 'application/octet-stream', test_admin_user.id, 1024)
    mock_file2 = await seed_file(file_id2, "file2", 'application/octet-stream', test_admin_user.id, 1024)
    all_files, total = await list_files(req, test_admin_user, None, 1, 15, None, None, None)
    assert file_id1 in [f["id"] for f in all_files ]
    assert file_id2 in [f["id"] for f in all_files ]
    assert total == 2

@pytest.mark.asyncio
async def test_list_files_by_api_key(make_request, seed_file, test_admin_user):
    """Test getting  listing files by user's api key."""
    req = make_request()
    file_id1 = uuid.uuid4()
    file_id2 = uuid.uuid4()
    mock_file1 = await seed_file(file_id1, "file1", 'application/octet-stream', test_admin_user.id, 1024)
    mock_file2 = await seed_file(file_id2, "file2", 'application/octet-stream', test_admin_user.id, 1024)
    mock_api_key_create_request = ApiKeyCreateRequest(name="test_key", key_type="personal", scopes=["file:read", "file:upload"],
                                                      expires_in_days=10, ngroup_id=uuid.UUID(test_admin_user.ngroups[0]))
    mock_api_key = await create_api_key(req, mock_api_key_create_request, test_admin_user)
    mock_file_list_request = FileListRequest(apiKey=str(mock_api_key["key"]), file_id=None, status=None,
                                             page=1, page_size=50, start_date=None, end_date=None)  

    file_list, total = await list_files_by_api_key(req, mock_file_list_request)

    assert file_id1 in [f["id"] for f in file_list ]
    assert file_id2 in [f["id"] for f in file_list ]
    assert total == 2

@pytest.mark.asyncio
async def test_list_files_by_api_key_file_id(make_request, seed_file, test_admin_user):
    """Test listing a file by api key and file id."""
    req = make_request()
    file_id1 = uuid.uuid4()
    file_id2 = uuid.uuid4()
    mock_file1 = await seed_file(file_id1, "file1", 'application/octet-stream', test_admin_user.id, 1024)
    mock_file2 = await seed_file(file_id2, "file2", 'application/octet-stream', test_admin_user.id, 1024)
    mock_api_key_create_request = ApiKeyCreateRequest(name="test_key", key_type="personal", scopes=["file:read", "file:upload"],
                                                      expires_in_days=10, ngroup_id=uuid.UUID(test_admin_user.ngroups[0]))
    mock_api_key = await create_api_key(req, mock_api_key_create_request, test_admin_user)
    mock_file_list_request = FileListRequest(apiKey=str(mock_api_key["key"]), file_id=str(file_id1), status=None,
                                             page=1, page_size=50, start_date=None, end_date=None) 

    file_list, total = await list_files_by_api_key(req, mock_file_list_request)

    assert file_id1 == file_list[0]["id"]
    assert total == 1

@pytest.mark.asyncio
async def test_list_files_by_api_key_invalid_api_key(make_request, seed_file, test_admin_user):
    """Test listing files by api key, but api key is invalid."""
    req = make_request()
    file_id = uuid.uuid4()
    await seed_file(file_id, "file1", 'application/octet-stream', test_admin_user.id, 1024)
    mock_file_list_request = FileListRequest(apiKey="invalid", file_id=None, status=None, page=1, page_size=50, start_date=None, end_date=None)  
    with pytest.raises(InvalidApiKeyError):
        await list_files_by_api_key(req, mock_file_list_request)

@pytest.mark.asyncio
async def test_list_files_by_api_key_api_key_no_data(make_request, seed_file, test_admin_user):
    """Test listing files by api key, but there is no data."""
    req = make_request()
    file_id = uuid.uuid4()
    await seed_file(file_id, "file1", 'application/octet-stream', test_admin_user.id, 1024)
    mock_file_list_request = FileListRequest(apiKey="cue_sk_", file_id=None, status=None, page=1, page_size=50, start_date=None, end_date=None)  
    with pytest.raises(InvalidApiKeyError):
        await list_files_by_api_key(req, mock_file_list_request)

@pytest.mark.asyncio
async def test_list_files_by_api_key_key_scope_error(make_request, test_admin_user):
    """Test listing files by api key but api key does not have correct scope."""
    req = make_request()
    file_id = uuid.uuid4()
    mock_api_key_create_request = ApiKeyCreateRequest(name="test_key", key_type="personal", scopes=["file:upload"], file_id=file_id, expires_in_days=10, ngroup_id=uuid.UUID(test_admin_user.ngroups[0]))
    mock_api_key = await create_api_key(req, mock_api_key_create_request, test_admin_user)
    mock_file_list_request = FileListRequest(apiKey=str(mock_api_key["key"]), file_id=None, status=None, page=1, page_size=50, start_date=None, end_date=None)  

    with pytest.raises(ApiKeyScopeError):
        await list_files_by_api_key(req, mock_file_list_request)


@pytest.mark.asyncio
async def test_list_files_by_api_key_file_file_id_file_access_error(make_request, seed_file, test_admin_user, seed_ngroup):
    """Test listing files by api key but file is in different ngroup."""
    req = make_request()
    file_id = uuid.uuid4()
    ngroup_id2 = uuid.uuid4() 
    await seed_ngroup(ngroup_id2, "test_ngroup2", "Test Ngroup 2")
    await seed_file(file_id, "file1", 'application/octet-stream', test_admin_user.id, 1024)
    mock_api_key_create_request = ApiKeyCreateRequest(name="test_key", key_type="personal", scopes=["file:read", "file:upload"], file_id=file_id, expires_in_days=10, ngroup_id=ngroup_id2)
    mock_api_key = await create_api_key(req, mock_api_key_create_request, test_admin_user)
    mock_file_list_request = FileListRequest(apiKey=str(mock_api_key["key"]), file_id=file_id, status=None, page=1, page_size=50, start_date=None, end_date=None)  

    with pytest.raises(FileAccessError):
        await list_files_by_api_key(req, mock_file_list_request)


@pytest.mark.asyncio
async def test_update_file(make_request, seed_file, test_admin_user):
    """Test updating file."""
    req = make_request()
    file_id = uuid.uuid4()
    mock_file = await seed_file(file_id, "file1", 'application/octet-stream', test_admin_user.id, 1024)
    mock_file_update_request = FileUpdateRequest(name="file_name_new", collection_path=None)

    updated_file = await update_file(req, mock_file["file"]["id"], mock_file_update_request)

    assert updated_file["id"] == file_id
    assert updated_file["name"] == mock_file_update_request.name
    assert updated_file["collection_path"] == mock_file_update_request.collection_path

@pytest.mark.asyncio
async def test_delete_file(make_request, seed_file, test_admin_user):
    """Test deleting file."""
    req = make_request()
    file_id = uuid.uuid4()
    mock_file = await seed_file(file_id, "file1", 'application/octet-stream', test_admin_user.id, 1024)

    await delete_file(req, file_id)








