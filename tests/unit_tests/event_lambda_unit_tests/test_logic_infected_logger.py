import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch
from botocore.exceptions import ClientError
from app.event_lambdas.infected_logger.model import ScanResultMessage
import os

@pytest.mark.asyncio
async def test_publish_infected_file_event(mock_boto3_client):
    from app.event_lambdas.infected_logger.logic import publish_infected_file_event

    key = uuid.uuid4()
    result = "Infected"
    date_scanned = datetime.now(tz=timezone.utc)
    scan_results = [{"result":result,
                     "virusName":["EICAR-AV-TEST"],
                     "message":["eicar.com"],
                     "dateScanned":date_scanned,
                     "engine":"Sophos"}]
    mock_scan_result_message = ScanResultMessage(key=key,
                                                result=result,
                                                dateScanned=date_scanned,
                                                scan_results=scan_results)

    await publish_infected_file_event(mock_scan_result_message)


@pytest.mark.asyncio
async def test_send_clean_file_message_sqs(mock_boto3_client):
    from app.event_lambdas.infected_logger.logic import send_clean_file_message_sqs

    mock_file_id = uuid.uuid4()
    mock_collection_id = uuid.uuid4()

    await send_clean_file_message_sqs(mock_file_id, mock_collection_id)

@pytest.mark.asyncio
async def test_send_clean_file_message_sqs_no_transfer_queue(mock_boto3_client):
    from app.event_lambdas.infected_logger.logic import send_clean_file_message_sqs
    with patch("app.event_lambdas.infected_logger.logic.CLEAN_FILES_QUEUE_URL", None):

        mock_file_id = uuid.uuid4()
        mock_collection_id = uuid.uuid4()

        await send_clean_file_message_sqs(mock_file_id, mock_collection_id)

@pytest.mark.asyncio
async def test_invoke_transfer_lambda(mock_boto3_client):
    from app.event_lambdas.infected_logger.logic import invoke_file_transfer_lambda

    mock_file_id = uuid.uuid4()
    mock_collection_id = uuid.uuid4()

    await invoke_file_transfer_lambda(mock_file_id, mock_collection_id)

@pytest.mark.asyncio
async def test_invoke_transfer_lambda_no_lambda_name(mock_boto3_client):
    from app.event_lambdas.infected_logger.logic import invoke_file_transfer_lambda
    with patch("app.event_lambdas.infected_logger.logic.FILE_TRANSFER_LAMBDA_NAME", None):

        mock_file_id = uuid.uuid4()
        mock_collection_id = uuid.uuid4()

        await invoke_file_transfer_lambda(mock_file_id, mock_collection_id)

@pytest.mark.asyncio
async def test_process_scan_result_clean(mock_boto3_client, seed_file, test_admin_user, connection_pool):
    from app.event_lambdas.infected_logger.logic import process_scan_result
    key = uuid.uuid4()
    result = "Clean"
    date_scanned = datetime.now(tz=timezone.utc)
   
    await seed_file(key, "test_file.txt", "text/plain", test_admin_user.id, 1024, scan_start=date_scanned, scan_end=date_scanned)


    scan_results = [{"result":result,
                     "virusName":[],
                     "message":[],
                     "dateScanned":date_scanned,
                     "engine":"Sophos"}]

    mock_scan_result_message = ScanResultMessage(key=key,
                                                result=result,
                                                dateScanned=date_scanned,
                                                scan_results=scan_results)
    await process_scan_result(mock_scan_result_message, connection_pool)
    # Check db?
    async with connection_pool.acquire() as conn:
        status = await conn.fetchval("SELECT status FROM file_status WHERE id = $1;", key)
    assert status == "clean"

@pytest.mark.asyncio
async def test_process_scan_result_clean_transfer_sqs(mock_boto3_client, seed_file, test_admin_user, connection_pool):
    from app.event_lambdas.infected_logger.logic import process_scan_result
    with patch("app.event_lambdas.infected_logger.logic.TRANSFER_INVOCATION_MODE", None):
        key = uuid.uuid4()
        result = "Clean"
        date_scanned = datetime.now(tz=timezone.utc)
   
        await seed_file(key, "test_file.txt", "text/plain", test_admin_user.id, 1024, scan_start=date_scanned, scan_end=date_scanned)


        scan_results = [{"result":result,
                        "virusName":[],
                        "message":[],
                        "dateScanned":date_scanned,
                        "engine":"Sophos"}]

        mock_scan_result_message = ScanResultMessage(key=key,
                                                    result=result,
                                                    dateScanned=date_scanned,
                                                    scan_results=scan_results)
        await process_scan_result(mock_scan_result_message, connection_pool)
        # Check db?
        async with connection_pool.acquire() as conn:
            status = await conn.fetchval("SELECT status FROM file_status WHERE id = $1;", key)
        assert status == "clean"
    
@pytest.mark.asyncio
async def test_process_scan_result_infected(mock_boto3_client, seed_file, test_admin_user, connection_pool):
    from app.event_lambdas.infected_logger.logic import process_scan_result

    key = uuid.uuid4()
    result = "Infected"
    date_scanned = datetime.now(tz=timezone.utc)
   
    await seed_file(key, "eicar.com", "text/plain", test_admin_user.id, 1024, scan_start=date_scanned, scan_end=date_scanned)


    scan_results = [{"result":result,
                     "virusName":["EICAR-AV-TEST"],
                     "message":["eicar.com"],
                     "dateScanned":date_scanned,
                     "engine":"Sophos"}]

    mock_scan_result_message = ScanResultMessage(key=key,
                                                result=result,
                                                dateScanned=date_scanned,
                                                scan_results=scan_results)
    await process_scan_result(mock_scan_result_message, connection_pool)
    async with connection_pool.acquire() as conn:
        status = await conn.fetchval("SELECT status FROM file_status WHERE id = $1;", key)
    assert status == "infected"

@pytest.mark.asyncio
async def test_process_scan_result_infected_at_threshold(mock_boto3_client, seed_file, test_admin_user, connection_pool):
    from app.event_lambdas.infected_logger.logic import process_scan_result
    with patch("app.event_lambdas.infected_logger.logic.INFECTED_FILE_THRESHOLD", 1):
        key = uuid.uuid4()
        result = "Infected"
        date_scanned = datetime.now(tz=timezone.utc)
   
        await seed_file(key, "eicar.com", "text/plain", test_admin_user.id, 1024, scan_start=date_scanned, scan_end=date_scanned)


        scan_results = [{"result":result,
                        "virusName":["EICAR-AV-TEST"],
                        "message":["eicar.com"],
                        "dateScanned":date_scanned,
                        "engine":"Sophos"}]

        mock_scan_result_message = ScanResultMessage(key=key,
                                                    result=result,
                                                    dateScanned=date_scanned,
                                                    scan_results=scan_results)
        await process_scan_result(mock_scan_result_message, connection_pool)
        async with connection_pool.acquire() as conn:
            status = await conn.fetchval("SELECT status FROM file_status WHERE id = $1;", key)
        assert status == "infected"

@pytest.mark.asyncio
async def test_process_scan_result_scan_failed(mock_boto3_client, seed_file, test_admin_user, connection_pool):
    from app.event_lambdas.infected_logger.logic import process_scan_result
    key = uuid.uuid4()
    result = "Scan Failed"
    date_scanned = datetime.now(tz=timezone.utc)
   
    await seed_file(key, "test_file.txt", "text/plain", test_admin_user.id, 1024, scan_start=date_scanned, scan_end=date_scanned)


    scan_results = [{"result":result,
                     "virusName":[],
                     "message":[],
                     "dateScanned":date_scanned,
                     "engine":"Sophos"}]

    mock_scan_result_message = ScanResultMessage(key=key,
                                                result=result,
                                                dateScanned=date_scanned,
                                                scan_results=scan_results)
    await process_scan_result(mock_scan_result_message, connection_pool)
    # Check db?
    async with connection_pool.acquire() as conn:
        status = await conn.fetchval("SELECT status FROM file_status WHERE id = $1;", key)
    assert status == "scan_failed"