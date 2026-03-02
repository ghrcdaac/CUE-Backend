import pytest
import uuid
from botocore.exceptions import ClientError


def test_manual_file_transfer(test_client, test_admin_user, make_jwt, mock_boto3_client):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}

    file_payload = {
        "file_ids":[str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]
    }

    response = test_client.post("v2/events/file_transfer", headers=headers, json=file_payload)
    response_json = response.json()
    assert response.status_code == 200
    assert response_json["status_code"] == 200
    assert response_json["body"]["message"] == "All file transfers initiated."


def test_manual_file_tranfser_failure(test_client, test_admin_user, make_jwt, mock_boto3_client):
    lambda_ = mock_boto3_client("lambda")
    lambda_.invoke.side_effect = ClientError({"Error":{"Message":"Forced Error", "Code":"invoke.failed"}}, operation_name="invoke")

    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}

    file_payload = {
        "file_ids":[str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]
    }

    response = test_client.post("v2/events/file_transfer", headers=headers, json=file_payload)
    response_json = response.json()
    assert response.status_code == 500
    assert response_json["detail"] == "Failed to invoke manual file transfer"