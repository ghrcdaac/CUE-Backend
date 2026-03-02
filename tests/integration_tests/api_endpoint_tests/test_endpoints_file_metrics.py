import pytest
import uuid
import random
import json
from app.v2.type_util.file_metrics import MetricsSummaryResponse, CostSummaryResponse, PaginatedCostByCollectionResponse, PaginatedCostByFileResponse
from pydantic import ValidationError


@pytest.mark.asyncio
async def test_get_metrics_summary_endpoint(test_client, test_admin_user, seed_test_files, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}
    # total 10 files
    file_details_seeding1 = await seed_test_files(test_admin_user.id, upload_offset=2)
    params = {} # no params full summary
    response = test_client.get("v2/file-metrics/summary", headers=headers, params=params)
    response_json = response.json()
    try:  
        validated_model = MetricsSummaryResponse.model_validate(response_json)
        assert validated_model.overall_count.value == file_details_seeding1["total_count"]
        assert validated_model.overall_volume.value == file_details_seeding1["total_volume"]
        assert validated_model.daily_count[0].value == file_details_seeding1["total_count"]
        assert validated_model.daily_volume[0].value == file_details_seeding1["total_volume"]
        seed_status_counts = file_details_seeding1["status_counts"]
        for status_count in validated_model.status_counts:
            assert seed_status_counts[status_count.status] == status_count.count

    except ValidationError as e:
        pytest.fail("{e}")

    # total 20 files 
    file_details_seeding2 = await seed_test_files(test_admin_user.id)
    total_count = file_details_seeding1["total_count"] + file_details_seeding2["total_count"]
    total_volume = file_details_seeding1["total_volume"] + file_details_seeding2["total_volume"]

    params = {} # no params full summary
    response = test_client.get("v2/file-metrics/summary", headers=headers, params=params)
    response_json = response.json()

    try:  
        validated_model = MetricsSummaryResponse.model_validate(response_json)
        assert validated_model.overall_count.value == total_count
        assert validated_model.overall_volume.value == total_volume
        assert validated_model.daily_count[0].value == file_details_seeding1["total_count"]
        assert validated_model.daily_volume[0].value == file_details_seeding1["total_volume"]
        assert validated_model.daily_count[0].value == file_details_seeding2["total_count"]
        assert validated_model.daily_volume[0].value == file_details_seeding2["total_volume"]
        seed_status_counts1 = file_details_seeding1["status_counts"]
        seed_status_counts2 = file_details_seeding2["status_counts"]
        for status_count in validated_model.status_counts:
            count_for_status = seed_status_counts1[status_count.status] + seed_status_counts2[status_count.status]
            assert count_for_status == status_count.count
    except ValidationError as e:
        pytest.fail("{e}")

@pytest.mark.asyncio
async def test_get_daily_volume_endpoint(test_client, test_admin_user, seed_test_files, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}
    two_days_ago_files = await seed_test_files(test_admin_user.id, upload_offset=2)
    yesterdays_files = await seed_test_files(test_admin_user.id, upload_offset=1)
    todays_files = await seed_test_files(test_admin_user.id)
    params = {}
    response = test_client.get("/v2/file-metrics/daily-volume", headers=headers, params=params)
    response_json = response.json()
    assert response.status_code == 200
    assert two_days_ago_files["total_volume"] == response_json[0]["value"]
    assert yesterdays_files["total_volume"] == response_json[0]["value"]
    assert todays_files["total_volume"] == response_json[0]["value"]

@pytest.mark.asyncio
async def test_get_daily_count_endpoint(test_client, test_admin_user, seed_test_files, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}
    two_days_ago_files = await seed_test_files(test_admin_user.id, upload_offset=2)
    yesterdays_files = await seed_test_files(test_admin_user.id, upload_offset=1)
    todays_files = await seed_test_files(test_admin_user.id)
    params = {}
    response = test_client.get("/v2/file-metrics/daily-count", headers=headers, params=params)
    response_json = response.json()
    assert response.status_code == 200
    assert two_days_ago_files["total_count"] == response_json[0]["value"]
    assert yesterdays_files["total_count"] == response_json[0]["value"]
    assert todays_files["total_count"] == response_json[0]["value"]

@pytest.mark.asyncio
async def test_get_overall_volume_endpoint(test_client, test_admin_user, seed_test_files, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}
    two_days_ago_files = await seed_test_files(test_admin_user.id, upload_offset=2)
    yesterdays_files = await seed_test_files(test_admin_user.id, upload_offset=1)
    todays_files = await seed_test_files(test_admin_user.id)
    params = {}
    response = test_client.get("/v2/file-metrics/overall-volume", headers=headers, params=params)
    response_json = response.json()
    total_volume = two_days_ago_files["total_volume"] + yesterdays_files["total_volume"] + todays_files["total_volume"]
    assert response.status_code == 200
    assert response_json["value"] == total_volume

@pytest.mark.asyncio
async def test_get_overall_count_endpoint(test_client, test_admin_user, seed_test_files, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}
    two_days_ago_files = await seed_test_files(test_admin_user.id, upload_offset=2)
    yesterdays_files = await seed_test_files(test_admin_user.id, upload_offset=1)
    todays_files = await seed_test_files(test_admin_user.id)
    params = {}
    response = test_client.get("/v2/file-metrics/overall-count", headers=headers, params=params)
    response_json = response.json()
    total_volume = two_days_ago_files["total_count"] + yesterdays_files["total_count"] + todays_files["total_count"]
    assert response.status_code == 200
    assert response_json["value"] == total_volume

@pytest.mark.asyncio
async def test_get_status_counts_endpoint(test_client, test_admin_user, seed_test_files, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}
    two_days_ago_files = await seed_test_files(test_admin_user.id, status_counts={"distributed": 5}, upload_offset=2)
    yesterdays_files = await seed_test_files(test_admin_user.id, status_counts={"distributed": 3, "infected": 1, "scan_failed": 1}, upload_offset=1)
    todays_files = await seed_test_files(test_admin_user.id, status_counts={"distributed": 3, "clean": 3})
    params = {} 
    response = test_client.get("/v2/file-metrics/status-counts", headers=headers, params=params)
    response_json = response.json()
    tda_status_counts, yd_status_counts, td_status_counts  = two_days_ago_files["status_counts"], yesterdays_files["status_counts"], todays_files["status_counts"]
    assert response.status_code == 200
    for status_count in response_json:
        status = status_count["status"]
        total_count = tda_status_counts.get(status,0) + yd_status_counts.get(status,0) + td_status_counts.get(status,0)
        assert status_count["count"] == total_count

@pytest.mark.asyncio
async def test_get_cost_summary_endpoint(test_client, test_admin_user, seed_test_files, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}
    two_days_ago_files = await seed_test_files(test_admin_user.id, upload_offset=2)
    yesterdays_files = await seed_test_files(test_admin_user.id, upload_offset=1)
    todays_files = await seed_test_files(test_admin_user.id)
    params = {}
    response = test_client.get("/v2/file-metrics/cost-summary", headers=headers, params=params)
    response_json = response.json()
    total_count = two_days_ago_files["total_count"] + yesterdays_files["total_count"] + todays_files["total_count"]
    total_volume = two_days_ago_files["total_volume"] + yesterdays_files["total_volume"] + todays_files["total_volume"]
    assert response.status_code == 200
    try:  
        validated_model = CostSummaryResponse.model_validate(response_json)
        for day in validated_model.daily_cost:
            assert day.value > 0.0
        assert validated_model.total_cost.value > 0.0
        assert validated_model.total_files == total_count
        assert validated_model.total_size_bytes == total_volume

    except ValidationError as e:
        pytest.fail(f"{e}")

@pytest.mark.asyncio
async def test_get_cost_by_collection_endpoint(test_client, test_admin_user, test_collection, seed_collection, seed_test_files, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}
    # test_collection acts as test_collection0
    test_collection1 = await seed_collection("test_collection1", True)
    test_collection2 = await seed_collection("test_collection2", True)
    c0_files = await seed_test_files(test_admin_user.id) 
    c1_files = await seed_test_files(test_admin_user.id, collection_id=test_collection1["id"]) 
    c2_files = await seed_test_files(test_admin_user.id, collection_id=test_collection2["id"]) 
    params = {"page":1, "page_size":50}
    response = test_client.get("/v2/file-metrics/cost-by-collection", headers=headers, params=params)
    response_json = response.json()
    assert response.status_code == 200
    try:
        validated_model = PaginatedCostByCollectionResponse.model_validate(response_json)
        validated_model.total = 3
        validated_model.page = params["page"]
        validated_model.page_size = params["page_size"]
        for item in validated_model.items:
            assert item.name in (test_collection["short_name"], test_collection1["short_name"], test_collection2["short_name"])
            assert item.size_bytes in (c0_files["total_volume"], c1_files["total_volume"], c2_files["total_volume"])
            assert item.cost > 0.0
    except ValidationError as e:
        pytest.fail(f"{e}")

@pytest.mark.asyncio
async def test_get_cost_by_file_endpoint(test_client, test_admin_user, seed_test_files, make_jwt):
    test_admin_user_jwt = make_jwt(sub=str(test_admin_user.id))
    headers = {"Authorization": f"Bearer {test_admin_user_jwt}", "x-active-ngroup-id": test_admin_user.active_ngroup_id}
    file_details = await seed_test_files(test_admin_user.id)
    params={
        "page": 1,
        "page_size": 50
    }
    response = test_client.get("v2/file-metrics/cost-by-file", headers=headers, params=params)
    response_json = response.json()
    assert response.status_code == 200
    try: 
        validated_model = PaginatedCostByFileResponse.model_validate(response_json)
        assert validated_model.total == file_details["total_count"] 
        assert validated_model.page == 1
        assert validated_model.page_size == 50
        for item in validated_model.items:
            assert item.name is not None
            assert item.size_bytes == 1024
            assert item.cost > 0.0

    except ValidationError as e:
       pytest.fail(f"{e}") 