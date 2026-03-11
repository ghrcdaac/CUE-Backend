import pytest
import uuid
import os 
from datetime import datetime, timezone, timedelta
from app.event_lambdas.notification_manager.logic import process_infected_scheduled_notification, create_text_part, create_file_table, process_providers_report
from app.event_lambdas.notification_manager.db import (
    get_infected_scheduled_file_details,
    get_providers_exceeding_threshold,
    mark_files_as_notified,
    mark_providers_as_notified
)

@pytest.mark.asyncio
async def test_process_infected_scheduled_notification(seed_file, seed_user, test_provider, connection_pool):
    """Test processing infected scheduled notification.""" 
    user_id = uuid.uuid4()
    await seed_user(user_id, "test_user@test.com", "test_user", "test user","0e686dba-e5b2-4302-aea0-e9ed0caff7d3", account_type="provider")

    for i in range(1, 6):
        file_id = uuid.uuid4()
        date_scanned = datetime.now(tz=timezone.utc) + timedelta(milliseconds=30)
        scan_results = f'[{{"ip_address":"127.0.0.1"}}, {{"engine":"Sophos","result":"Infected","message":["{file_id}"],"virusName":["EICAR-AV-Test"],"dateScanned":"{date_scanned}"}}]'
        await seed_file(file_id, f"file{i}", 'application/octet-stream',
                        user_id, 1024, status="infected",
                        scan_start=date_scanned, scan_end=date_scanned, scan_results=scan_results)

    # simulate can_upload block   
    async with connection_pool.acquire() as conn:
        await conn.execute("""UPDATE provider 
                              SET can_upload=False,
                                  reason='Provider automatically blocked after uploading 5 infected files within 24 hour(s) (Threshold: 5.'
                              WHERE id = $1
                     """, test_provider["id"])

    provider_lookback_window = timedelta(hours=24)
    infected_file_threshold = 5 

    notification_details = {}
    providers_exceeding_threshold = []
    async with connection_pool.acquire() as conn:
        scan_results = await conn.fetch("SELECT scan_results FROM file_status;")
        notification_details = await get_infected_scheduled_file_details(conn)
        providers_exceeding_threshold = await get_providers_exceeding_threshold(conn, provider_lookback_window, infected_file_threshold)
    
    file_ids_to_mark = [
        file['file_id'] 
        for ngroup_data in (notification_details or {}).values() 
        for file in ngroup_data.get('file_details', [])
    ]
        
    provider_ids_to_mark = [
        provider['provider_id'] 
        for ngroup_data in (providers_exceeding_threshold or {}).values() 
        for provider in ngroup_data
    ]
    async with connection_pool.acquire() as conn:
         async with conn.transaction():
            if file_ids_to_mark:
                await mark_files_as_notified(conn, file_ids_to_mark)
            if provider_ids_to_mark:
                await mark_providers_as_notified(conn, provider_ids_to_mark)
    for ngroup_id, infected_file_details in notification_details.items():
        provider_report_details = providers_exceeding_threshold.get(ngroup_id, []) 
        subject, html_details, body_text = await process_infected_scheduled_notification(
            infected_file_details, 
            provider_report_details 
        )
        assert subject == "CUE Security Alert: 5 Infected Files Detected - test_group"
        assert html_details.get("header") and html_details.get("files") 

@pytest.mark.asyncio
async def test_process_infected_scheduled_notification_single_file(seed_file, seed_user, test_provider, connection_pool):
    """Test processing infected scheduled notification for one file.""" 
    user_id = uuid.uuid4()
    await seed_user(user_id, "test_user@test.com", "test_user", "test user","0e686dba-e5b2-4302-aea0-e9ed0caff7d3", account_type="provider")

    for i in range(1, 2):
        file_id = uuid.uuid4()
        date_scanned = datetime.now(tz=timezone.utc) + timedelta(milliseconds=30)
        scan_results = f'[{{"ip_address":"127.0.0.1"}},{{"engine":"Sophos","result":"Infected","message":["{file_id}"],"virusName":["EICAR-AV-Test"],"dateScanned":"{date_scanned}"}}]'
        await seed_file(file_id, f"file{i}", 'application/octet-stream', user_id, 1024, status="infected", scan_start=date_scanned, scan_end=date_scanned, scan_results=scan_results)

    provider_lookback_window = timedelta(hours=24)
    infected_file_threshold = 5 

    notification_details = {}
    providers_exceeding_threshold = []
    async with connection_pool.acquire() as conn:
        scan_results = await conn.fetch("SELECT scan_results FROM file_status;")
        notification_details = await get_infected_scheduled_file_details(conn)
        providers_exceeding_threshold = await get_providers_exceeding_threshold(conn, provider_lookback_window, infected_file_threshold)
    
    file_ids_to_mark = [
        file['file_id'] 
        for ngroup_data in (notification_details or {}).values() 
        for file in ngroup_data.get('file_details', [])
    ]
        
    provider_ids_to_mark = [
        provider['provider_id'] 
        for ngroup_data in (providers_exceeding_threshold or {}).values() 
        for provider in ngroup_data
    ]
    async with connection_pool.acquire() as conn:
         async with conn.transaction():
            if file_ids_to_mark:
                await mark_files_as_notified(conn, file_ids_to_mark)
            if provider_ids_to_mark:
                await mark_providers_as_notified(conn, provider_ids_to_mark)
    for ngroup_id, infected_file_details in notification_details.items():
        provider_report_details = providers_exceeding_threshold.get(ngroup_id, []) 
        subject, html_details, body_text = await process_infected_scheduled_notification(
            infected_file_details, 
            provider_report_details 
        )
        assert subject == "CUE Security Alert: Infected File Detected - test_group"
        assert html_details.get("header") and html_details.get("files") 

@pytest.mark.asyncio
async def test_process_infected_scheduled_notification_file_details_is_not_list(seed_file, test_provider, connection_pool):
    """Test processing infected scheduled notification file details is not a list"""
    infected_file_details = {'short_name': 'test_group', 'recipient_emails': ['test_admin_user@test.com'], "file_details":"file_details"}
    providers_exceeding_threshold = []
    

    subject, html_details, body_text = await process_infected_scheduled_notification(infected_file_details, providers_exceeding_threshold)
    assert subject == "CUE Security Alert: Provider Threshold Report - test_group"
    assert html_details == {'files': '<p>No new infected file details in this interval.</p>',
                            'header': 'CUE Security Alert: Provider Threshold Report - test_group',
                            'first_line': 'No new infected files were detected in the last period.', 
                            'provider_intro': '', 'providers': '',
                            'end_line': 'Infected files are handled according to security protocols. Blocked providers require manual review in the CUE Dashboard to re-enable uploads.', 'ngroup_name_from_providers': 'test_group'}

@pytest.mark.asyncio
async def test_process_infected_scheduled_notification_no_file_details_with_provider(seed_file, test_provider, connection_pool):
    """Test process infected scheduled notification only block the provider."""
    infected_file_details = {'short_name': 'test_group', 'recipient_emails': ['test_admin_user@test.com']}
    provider_exceeding_threshold = [{'provider_id': f'{test_provider["id"]}', 'provider_name': 'test_provider', 'current_reason': 'Provider automatically blocked after uploading 5 infected files within 24 hour(s) (Threshold: 5.', 'is_currently_blocked': True}]
    
    async with connection_pool.acquire() as conn:
        await conn.execute("""UPDATE provider 
                        SET can_upload=False,
                            reason='Provider automatically blocked after uploading 5 infected files within 24 hour(s) (Threshold: 5.'
                        WHERE id = $1
                     """, test_provider["id"])

    subject, html_details, body_text = await process_infected_scheduled_notification(infected_file_details, provider_exceeding_threshold)

    assert subject == "CUE Security Alert: Provider Threshold Report - test_group"
    assert {'files': '<p>No new infected file details in this interval.</p>',
            'header': 'CUE Security Alert: Provider Threshold Report - test_group',
            'first_line': 'No new infected files were detected in the last period.',
            'provider_intro': 'Additionally, the following providers exceeded the infected file upload threshold during this period.',
            'providers': '\n    <div>\n        <table>\n            <tr>\n                <th>Provider Name</th>\n                <th>Currently Blocked?</th>\n                <th>Reason</th>\n            </tr>\n    \n            <tr>\n                <td>test_provider</td>\n                <td>Yes</td>\n                <td>Provider automatically blocked after uploading 5 infected files within 24 hour(s) (Threshold: 5.</td>\n            </tr>\n        \n        </table>\n        <p>Providers are blocked automatically by the system. To allow these providers to upload again, review their status and enable their "Can upload" permission in the CUE Dashboard.</p>\n    </div>\n    ', 'end_line': 'Infected files are handled according to security protocols. Blocked providers require manual review in the CUE Dashboard to re-enable uploads.',
            'ngroup_name_from_providers': 'test_group'}

@pytest.mark.asyncio
async def test_create_text_part():
    """Test creating text part."""
    file_details = {'file_name':'mock_file', 'uploader_name':'test_user', 'uploader_ip':'127.0.0.1', 'collection_name':"test_collection", 'virusName_processed':'EICAR AV TEST'}
    result = await create_text_part(file_details)
    expected_text = (
        f"File Name: {file_details.get('file_name', 'N/A')}\n"
        f"Uploaded By: {file_details.get('uploader_name', 'N/A')}\n"
        f"Uploader IP: {file_details.get('uploader_ip', 'N/A')}\n"
        f"Collection: {file_details.get('collection_name', 'N/A')}\n"
        f"Detected Threats: {file_details.get('virusName_processed', 'N/A')}\n"
        f"File ID: {file_details.get('file_id', 'N/A')}\n\n"
    )
    assert result == expected_text

@pytest.mark.asyncio
async def test_create_file_table():
    """Test creating file table for email."""
    file_details = {'file_name':'mock_file', 'uploader_name':'test_user', 'uploader_ip':'127.0.0.1', 'collection_name':"test_collection", 'virusName_processed':'EICAR AV TEST'}
    result =  await create_file_table(file_details)
    expected_table = f"""
    <table>
        <tr>
            <th>File Name</th>
            <td>{file_details.get("file_name", "N/A")}</td>
        </tr>
        <tr>
            <th>Uploaded By</th>
            <td>{file_details.get("uploader_name", "N/A")}</td>
        </tr>
        <tr>
            <th>Uploader IP Address</th>
            <td>{file_details.get("uploader_ip", "N/A")}</td>
        </tr>
        <tr>
            <th>Collection</th>
            <td>{file_details.get("collection_name", "N/A")}</td>
        </tr>
        <tr>
            <th>Date Scanned</th>
            <td>{file_details.get("date_scanned", "N/A")}</td>
        </tr>
        <tr>
            <th>Scan Result</th>
            <td><strong>{file_details.get("scan_result", "N/A")}</strong></td>
        </tr>
        <tr>
            <th>Detected Threats</th>
            <td>{file_details.get("virusName_processed", "N/A")}</td>
        </tr>
        <tr>
            <th>File ID (Key)</th>
            <td><small>{file_details.get("file_id", "N/A" )}</small></td>
        </tr>
    </table>
    """
    assert result == expected_table


@pytest.mark.asyncio
async def test_process_providers_report():
    """Test process providers portion of report."""
    mock_providers_over_threshold = [{"provider_name":"mock_provider1",
                                     "is_currently_blocked":True,
                                     "current_reason":"testing"},
                                     {"provider_name":"mock_provider2",
                                     "is_currently_blocked":True,
                                     "current_reason":"testing"}]
    result = await process_providers_report(mock_providers_over_threshold)
    expected_provider_html = """
    <div>
        <table>
            <tr>
                <th>Provider Name</th>
                <th>Currently Blocked?</th>
                <th>Reason</th>
            </tr>
            <tr>
                <td>mock_provider1</td>
                <td>Yes</td>
                <td>testing</td>
            </tr>
            <tr>
                <td>mock_provider2</td>
                <td>Yes</td>
                <td>testing</td>
            </tr>
        </table>
        <p>Providers are blocked automatically by the system. To allow these providers to upload again, review their status and enable their "Can upload" permission in the CUE Dashboard.</p>
    </div>
    """
    expected_text_parts= "".join(["\n--- Providers Exceeding Threshold ---\n","Provider: mock_provider1, Blocked: Yes, Reason: testing\n","Provider: mock_provider2, Blocked: Yes, Reason: testing\n"])

    assert "".join(result[0].split()) == "".join(expected_provider_html.split())
    assert "".join(result[1].split()) == "".join(expected_text_parts.split())