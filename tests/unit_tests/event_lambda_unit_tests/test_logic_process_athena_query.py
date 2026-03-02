import pytest
import csv 
import io
import json
import uuid
from botocore.exceptions import ClientError
from app.event_lambdas.process_athena_query.logic import store_result_in_s3, get_query_results_as_json, parse_csv_to_json, get_query_error_reason, QueryProcessingError

@pytest.mark.asyncio
async def test_get_query_results_as_json(mock_boto3_client):
    mock_query_execution_id = str(uuid.uuid4())
    results = await get_query_results_as_json(mock_query_execution_id)
    assert isinstance(results, str)
    try:
        json_result = json.loads(results)
        assert isinstance(json_result, list)
    except (json.JSONDecodeError, Exception):
        pytest.fail("result is not valid JSON") 

@pytest.mark.asyncio
async def test_get_query_results_as_json_clienterror(mock_boto3_client):
    athena = mock_boto3_client("athena")
    athena.get_query_execution.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"get_query_execution.failed"}}, operation_name="get_query_execution")

    mock_query_execution_id = str(uuid.uuid4())
    with pytest.raises(QueryProcessingError):
        await get_query_results_as_json(mock_query_execution_id)

@pytest.mark.asyncio
async def test_parse_csv_to_json(mock_boto3_client):
    data  = [["field1","field2","field3"], ["value1_1","","value1_3"], ["value1_2","value2_2","value2_3"], ["value1_3","value2_3","value3_3"]]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(data)
    mock_csv = output.getvalue()

    result = await parse_csv_to_json(mock_csv)
    expected_json = [{"field1":"value1_1", "field2":None, "field3": "value1_3"}, {"field1":"value1_2", "field2":"value2_2", "field3": "value2_3"}, {"field1":"value1_3", "field2":"value2_3", "field3": "value3_3"}]
    assert expected_json == result

@pytest.mark.asyncio
async def test_get_query_error_reason(mock_boto3_client):
    mock_query_execution_id = str(uuid.uuid4())
    result = await get_query_error_reason(mock_query_execution_id)
    assert result == "testing"

@pytest.mark.asyncio
async def test_get_query_error_reason_clienterror(mock_boto3_client):
    athena = mock_boto3_client("athena")
    athena.get_query_execution.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"get_query_execution.failed"}}, operation_name="get_query_execution")

    mock_query_execution_id = str(uuid.uuid4())
    result = await get_query_error_reason(mock_query_execution_id) 
    assert result == "Failed to retrieve error reason due to an AWS error."

@pytest.mark.asyncio
async def test_store_result_in_s3(mock_boto3_client):
    mock_query_execution_id = str(uuid.uuid4())
    result_json = json.dumps({"mock_key": "mock_value"})
    key = f"{mock_query_execution_id}.json"
    await store_result_in_s3(result_json, key)

@pytest.mark.asyncio
async def test_store_result_in_s3_clienterror(mock_boto3_client):
    s3 = mock_boto3_client("s3")
    s3.put_object.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"put_object.failed"}}, operation_name="put_object")
    mock_query_execution_id = str(uuid.uuid4())
    result_json = json.dumps({"mock_key": "mock_value"})
    key = f"{mock_query_execution_id}.json"
    with pytest.raises(QueryProcessingError):
        await store_result_in_s3(result_json, key)