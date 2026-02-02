import pytest
import json
import uuid
import hashlib
import base64
from unittest.mock import patch
from botocore.exceptions import ClientError

from app.event_lambdas.file_transfer.logic import (
    parse_sqs_message, process_messages, verify_staging_object_sha256,
    copy_file_to_dest, add_tags_to_dest, batch_transfer_and_validate,
    update_database_records)
from app.event_lambdas.file_transfer.db import fetch_batch_transfer_details

@pytest.mark.asyncio
async def test_parse_sqs_message(mock_boto3_client):
    mock_body = {"body": '{"mock_body": "mock_value"}'}
    body_dict = json.loads(mock_body["body"])
    parsed_message = await parse_sqs_message(mock_body)
    assert parsed_message == body_dict

@pytest.mark.asyncio
async def test_parse_sqs_message_empty_body(mock_boto3_client):
    mock_body = {"body": None}
    assert await parse_sqs_message(mock_body) is None

@pytest.mark.asyncio
async def test_parse_sqs_message_invalid_body(mock_boto3_client):
    mock_body = {"body": "invalid_body"}
    assert await parse_sqs_message(mock_body) is None

@pytest.mark.asyncio
async def test_process_messages(mock_boto3_client):
    collection_id = uuid.uuid4()
    mock_records = [{"messageId":str(uuid.uuid4()), "body":f'{{"file_id":"{str(uuid.uuid4())}","collection_id":"{collection_id}"}}'},{"messageId":str(uuid.uuid4()), "body":f'{{"file_id":"{str(uuid.uuid4())}","collection_id":"{collection_id}"}}'}]
    messages, file_ids = await process_messages(mock_records)
    for message_body in messages.values():
        assert uuid.UUID(message_body["file_id"]) in file_ids
        assert uuid.UUID(message_body["collection_id"]) == collection_id

@pytest.mark.asyncio
async def test_verify_staging_object_sha256(mock_boto3_client):
    file_id = uuid.uuid4()
    mock_s3_client = mock_boto3_client("s3")
    mock_file_response = mock_s3_client.get_object(Bucket="cue_staging_test", Key="mock_file")
    body = mock_file_response["Body"] 
    sha256_hash = hashlib.sha256()
    for chunk in body.iter_chunks(chunk_size=8192 * 1024): # 8MB chunks
        sha256_hash.update(chunk)

    calculated_hash = base64.b64encode(sha256_hash.digest()).decode('utf8')
    result_hash = await verify_staging_object_sha256(file_id)
    assert calculated_hash == result_hash

@pytest.mark.asyncio
async def test_copy_file_to_dest(mock_boto3_client, test_collection):
    file_id = uuid.uuid4()
    mock_file_info = {"name": "mock_file", "checksum":"mock_checksum",
                      "collection_path":None, "size_bytes":1024,
                      "collection_id":test_collection["id"]}
    src_key = str(file_id) 
    dest_bucket = "mock_dest_bucket"
    dest_key = "mock_dest_key"
    await copy_file_to_dest(src_key, dest_bucket, dest_key, mock_file_info)

@pytest.mark.asyncio
async def test_copy_file_to_dest_clienterror_transient(mock_boto3_client, test_collection):
    s3 = mock_boto3_client("s3")
    s3.copy_object.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"InternalError"}}, operation_name="copy_object") 
    file_id = uuid.uuid4()
    mock_file_info = {"name": "mock_file", "checksum":"mock_checksum",
                      "collection_path":None, "size_bytes":1024,
                      "collection_id":test_collection["id"]}
    src_key = str(file_id) 
    dest_bucket = "mock_dest_bucket"
    dest_key = "mock_dest_key"
    with pytest.raises(ClientError):
        await copy_file_to_dest(src_key, dest_bucket, dest_key, mock_file_info)

#@pytest.mark.asyncio
#async def test_copy_file_to_dest_clienterror_persistent(mock_boto3_client, test_collection):
    #s3 = mock_boto3_client("s3")
    #s3.copy_object.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"PersistentError"}}, operation_name="copy_object") 
    #file_id = uuid.uuid4()
    #mock_file_info = {"name": "mock_file", "checksum":"mock_checksum",
                      #"collection_path":None, "size_bytes":1024,
                      #"collection_id":test_collection["id"]}
    #src_key = str(file_id) 
    #dest_bucket = "mock_dest_bucket"
    #dest_key = "mock_dest_key"
    #with pytest.raises(ClientError):
        #await copy_file_to_dest(src_key, dest_bucket, dest_key, mock_file_info)

@pytest.mark.asyncio
async def test_add_tags_to_dest(mock_boto3_client):
    dest_bucket = "mock_dest_bucket"
    dest_key = "mock_dest_key"
    file_id = uuid.uuid4()
    await add_tags_to_dest(dest_bucket, dest_key, file_id)


@pytest.mark.asyncio
async def test_batch_transfer_and_validate(mock_boto3_client, seed_file, test_admin_user, test_collection, connection_pool):
    message_id1 = uuid.uuid4()
    message_id2 = uuid.uuid4()
    message_id3 = uuid.uuid4()
    file_id1 = str(uuid.uuid4())
    file_id2 = str(uuid.uuid4())
    file_id3 = str(uuid.uuid4())
    await seed_file(file_id1, "file1", 'application/octet-stream', test_admin_user.id, 1024, status="clean", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
    await seed_file(file_id2, "file2", 'application/octet-stream', test_admin_user.id, 1024, status="clean", checksum="bad_check_sum")
    await seed_file(file_id3, "file3", 'application/octet-stream', test_admin_user.id, 1024, status="clean", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
    file_ids = [file_id1, file_id2, file_id3]
    messages= {message_id1:{"file_id":file_id1, "collection_id": test_collection["id"]},
               message_id2:{"file_id":file_id2, "collection_id": test_collection["id"]},
               message_id3:{"file_id":file_id3, "collection_id": test_collection["id"]}}
    transfer_details = {}
    async with connection_pool.acquire() as conn:
        transfer_details = await fetch_batch_transfer_details(conn, file_ids)

    successful_ids, validation_failures, hard_failures = await batch_transfer_and_validate(messages, transfer_details)
    assert len(successful_ids) == 2 
    assert len(validation_failures) == 1
    assert hard_failures == []

@pytest.mark.asyncio
async def test_batch_transfer_and_validate_skip_validation(mock_boto3_client, seed_file, test_admin_user, test_collection, connection_pool):
    with patch("app.event_lambdas.file_transfer.logic.VERIFY_CHECKSUM", False):
        message_id1 = uuid.uuid4()
        message_id2 = uuid.uuid4()
        message_id3 = uuid.uuid4()
        file_id1 = str(uuid.uuid4())
        file_id2 = str(uuid.uuid4())
        file_id3 = str(uuid.uuid4())
        await seed_file(file_id1, "file1", 'application/octet-stream', test_admin_user.id, 1024, status="clean", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
        await seed_file(file_id2, "file2", 'application/octet-stream', test_admin_user.id, 1024, status="clean", checksum="bad_check_sum")
        await seed_file(file_id3, "file3", 'application/octet-stream', test_admin_user.id, 1024, status="clean", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
        file_ids = [file_id1, file_id2, file_id3]
        messages= {message_id1:{"file_id":file_id1, "collection_id": test_collection["id"]},
                message_id2:{"file_id":file_id2, "collection_id": test_collection["id"]},
                message_id3:{"file_id":file_id3, "collection_id": test_collection["id"]}}
        transfer_details = {}
        async with connection_pool.acquire() as conn:
            transfer_details = await fetch_batch_transfer_details(conn, file_ids)

        successful_ids, validation_failures, hard_failures = await batch_transfer_and_validate(messages, transfer_details)
        assert len(successful_ids) == 3 
        assert len(validation_failures) == 0
        assert hard_failures == []

@pytest.mark.asyncio
async def test_batch_transfer_and_validate_hard_failures_clienterror(mock_boto3_client, seed_file, test_admin_user, test_collection, connection_pool):
    s3 = mock_boto3_client("s3")
    s3.copy_object.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"PersistentError"}}, operation_name="copy_object") 

    message_id1 = uuid.uuid4()
    message_id2 = uuid.uuid4()
    message_id3 = uuid.uuid4()
    file_id1 = str(uuid.uuid4())
    file_id2 = str(uuid.uuid4())
    file_id3 = str(uuid.uuid4())
    await seed_file(file_id1, "file1", 'application/octet-stream', test_admin_user.id, 1024, status="clean", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
    await seed_file(file_id2, "file2", 'application/octet-stream', test_admin_user.id, 1024, status="clean", checksum="bad_check_sum")
    await seed_file(file_id3, "file3", 'application/octet-stream', test_admin_user.id, 1024, status="clean", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
    file_ids = [file_id1, file_id2, file_id3]
    messages= {message_id1:{"file_id":file_id1, "collection_id": test_collection["id"]},
            message_id2:{"file_id":file_id2, "collection_id": test_collection["id"]},
            message_id3:{"file_id":file_id3, "collection_id": test_collection["id"]}}
    transfer_details = {}
    async with connection_pool.acquire() as conn:
        transfer_details = await fetch_batch_transfer_details(conn, file_ids)

    successful_ids, validation_failures, hard_failures = await batch_transfer_and_validate(messages, transfer_details)
    assert len(successful_ids) == 0 
    assert len(validation_failures) == 0
    assert len(hard_failures) == 3 

@pytest.mark.asyncio
async def test_batch_transfer_and_validate_hard_failures_no_dest_bucket(mock_boto3_client, seed_file, test_admin_user, test_collection, test_ngroup_id):
    message_id1 = uuid.uuid4()
    message_id2 = uuid.uuid4()
    message_id3 = uuid.uuid4()
    file_id1 = str(uuid.uuid4())
    file_id2 = str(uuid.uuid4())
    file_id3 = str(uuid.uuid4())
    await seed_file(file_id1, "file1", 'application/octet-stream', test_admin_user.id, 1024, status="clean", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
    await seed_file(file_id2, "file2", 'application/octet-stream', test_admin_user.id, 1024, status="clean", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
    await seed_file(file_id3, "file3", 'application/octet-stream', test_admin_user.id, 1024, status="clean", checksum="7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=")
    file_ids = [file_id1, file_id2, file_id3]
    messages= {message_id1:{"file_id":file_id1, "collection_id": test_collection["id"]},
            message_id2:{"file_id":file_id2, "collection_id": test_collection["id"]},
            message_id3:{"file_id":file_id3, "collection_id": test_collection["id"]}}
    #transfer_details = {}
    #async with connection_pool.acquire() as conn:
    transfer_details = {uuid.UUID(file_id1): {'file_info': {'name': 'file1', 'checksum': '7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=', 'collection_path': None, 'size_bytes': 1024, 'collection_id': test_ngroup_id},
                                   'egress': {'path': '/data', 'config': {'destination_path': '/data/new_data'}}},
                        uuid.UUID(file_id2): {'file_info': {'name': 'file2', 'checksum': '7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=', 'collection_path': None, 'size_bytes': 1024, 'collection_id': test_ngroup_id},
                                    'egress': {'path': '/data', 'config': {'destination_path': '/data/new_data'}}},
                        uuid.UUID(file_id3): {'file_info': {'name': 'file3', 'checksum': '7Hwzs/KxphOh7+KgkOmSKRoOYQsqUuU1E9gMQo0UtHM=', 'collection_path': None, 'size_bytes': 1024, 'collection_id': test_ngroup_id},
                                    'egress': {'path': '/data', 'config': {'destination_path': '/data/new_data'}}}}

    successful_ids, validation_failures, hard_failures = await batch_transfer_and_validate(messages, transfer_details)
    assert len(successful_ids) == 0 
    assert len(validation_failures) == 0
    assert len(hard_failures) == 3 

@pytest.mark.asyncio
async def test_update_database_records(connection_pool, seed_file, test_admin_user):
    file1 = await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, status="clean")
    file2 = await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, status="clean")
    result = await update_database_records([file1["file"]["id"]],
                                           [{"file_id":file2["file"]["id"],
                                             "db_checksum":file2["file"]["checksum"],
                                             "staging_checksum":"mock_staging_checksum" }],
                                            connection_pool)
    assert result == (True,True)
    async with connection_pool.acquire() as conn:
        file1_status = await conn.fetchval("SELECT status from file_status where id = $1", file1["file"]["id"])
        file2_status = await conn.fetchval("SELECT status from file_status where id = $1", file2["file"]["id"])
    assert file1_status == 'distributed'
    assert file2_status == 'distributed'

@pytest.mark.asyncio
async def test_update_database_records_exception_during_update(connection_pool, seed_file, test_admin_user):
    with patch("app.event_lambdas.file_transfer.logic.asyncio.gather") as update_success_mock:
        update_success_mock.side_effect=Exception("Forced DB Error")
        file1 = await seed_file(uuid.uuid4(), "file1", 'application/octet-stream', test_admin_user.id, 1024, status="clean")
        file2 = await seed_file(uuid.uuid4(), "file2", 'application/octet-stream', test_admin_user.id, 1024, status="clean")
        result = await update_database_records([file1["file"]["id"]],
                                            [{"file_id":file2["file"]["id"],
                                                "db_checksum":file2["file"]["checksum"],
                                                "staging_checksum":"mock_staging_checksum" }],
                                                connection_pool)
        assert result == (False,False)

@pytest.mark.asyncio
async def test_update_database_records_empty_lists(connection_pool, seed_file, test_admin_user):
    result = await update_database_records([], [], connection_pool)
    assert result == (True,True)