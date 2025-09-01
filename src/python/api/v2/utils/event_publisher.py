import os
import boto3
import json
from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)

# Initialize the EventBridge client once per container for reuse
eventbridge_client = boto3.client('events', region_name=os.environ.get("AWS_REGION", "us-west-2"))
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "cue-application-bus")

def publish_event(source: str, detail_type: str, detail: Dict[str, Any]):
    """
    Publishes a custom event to the application's EventBridge bus.

    Args:
        source (str): The source of the event (e.g., 'com.cue.api').
        detail_type (str): The type of event (e.g., 'UserApplicationSubmitted').
        detail (Dict[str, Any]): The payload of the event.
    """
    if not EVENT_BUS_NAME:
        logger.error("event.publish.failed", reason="EVENT_BUS_NAME environment variable not set.")
        return

    logger.info("event.publish.started", source=source, detail_type=detail_type, detail=detail)
    try:
        entry = {
            'Source': source,
            'DetailType': detail_type,
            'Detail': json.dumps(detail),
            'EventBusName': EVENT_BUS_NAME
        }
        response = eventbridge_client.put_events(Entries=[entry])
        
        failed_count = response.get('FailedEntryCount', 0)
        if failed_count > 0:
            logger.error("event.publish.failed", source=source, detail_type=detail_type, response=response)
        else:
            logger.info("event.publish.success", source=source, detail_type=detail_type)
            
    except Exception:
        logger.error(
            "event.publish.exception", 
            source=source, 
            detail_type=detail_type, 
            exc_info=True
        )
