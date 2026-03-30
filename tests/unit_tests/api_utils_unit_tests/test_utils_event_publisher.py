import pytest
from unittest.mock import patch
from app.v2.utils.event_publisher import publish_event

@pytest.mark.asyncio
async def test_publish_event(mock_boto3_client):
    """Test publishing an event."""
    mock_source = "source"
    mock_detail_type = "mock_detail_type"
    mock_detail = {"mock_detail": "mock_detail_value"}

    publish_event(mock_source, mock_detail_type, mock_detail)

@pytest.mark.asyncio
async def test_publish_event_no_event_bus_name(mock_boto3_client):
    """Test publishing an event but EVENT_BUS_NAME is not configured"""
    with patch("app.v2.utils.event_publisher.EVENT_BUS_NAME", None):
        mock_source = "source"
        mock_detail_type = "mock_detail_type"
        mock_detail = {"mock_detail": "mock_detail_value"}

        publish_event(mock_source, mock_detail_type, mock_detail)


@pytest.mark.asyncio
async def test_publish_event_event_non_zero_failed_count(mock_boto3_client):
    """Test publishing events event but there was partial failure """
    events = mock_boto3_client("events")
    events.put_events.side_effect=None
    events.put_events.return_value = {'FailedEntryCount': 2,
                                       'Entries': {"entry":"failed_entry"},
                                       'EventId': 'mock_eventId',
                                       'ErrorCode': 'mock_error_code',
                                       'ErrorMessage': 'mock_error_message'}
    mock_source = "source"
    mock_detail_type = "mock_detail_type"
    mock_detail = {"mock_detail": "mock_detail_value"}

    publish_event(mock_source, mock_detail_type, mock_detail)