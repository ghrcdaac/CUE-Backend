import pytest
import uuid

from fastapi import HTTPException 
from app.v2.utils.authorization import check_user_access_to_file
from app.v2.utils.cueuser import get_user_profile
from app.v2.type_util.auth import AuthUser 

@pytest.mark.asyncio
async def test_check_user_access_to_file(make_request, test_admin_user, seed_file, seed_user, seed_ngroup, seed_provider, seed_egress, seed_collection):
    # Test admin access
    req = make_request()
    file_id = uuid.uuid4()

    await seed_file(file_id, "file", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await check_user_access_to_file(req, test_admin_user, file_id)

    # Test daac_manager access
    # daac_manager 
    role_id="ef872fe7-92b9-45ec-ac19-80f4c478fd36" 
    user_id = uuid.uuid4()
    await seed_user(user_id, "test_email@test.com", "test_username_user", "test_user", role_id)
    dm_profile = await get_user_profile(req, user_id)

    mock_daac_manager_auth_user = AuthUser(id=dm_profile["id"],
                                           email=dm_profile["email"],
                                           cueusername=dm_profile["cueusername"],
                                           name=dm_profile["name"],
                                           roles=dm_profile["roles"],
                                           ngroups=[str(dm_profile["ngroups"][0]["id"])],
                                           privileges=dm_profile["privileges"],
                                           active_ngroup_id=str(dm_profile["ngroups"][0]["id"]))
    await check_user_access_to_file(req, mock_daac_manager_auth_user, file_id)

    # Test access outside of ngroup
    ngroup2 = await seed_ngroup(uuid.uuid4(), "test_ngroup2", "Test Ngroup 2")
    egress2 = await seed_egress("s3", "/data", {"destination_path":"/sub_folder"}, ngroup2["id"])
    provider2 = await seed_provider("test_ngroup_2_provider", "Test Ngroup 2 Provider", True, test_admin_user.id, ngroup_id=ngroup2["id"])

    user_id2 = uuid.uuid4()
    #provider_id
    role_id2="ef872fe7-92b9-45ec-ac19-80f4c478fd36" 
    mock_provider_user = await seed_user(user_id2, "test_email2@test.com", "test_username_user2", "test_user", role_id2, ngroup_id=ngroup2["id"], account_type="provider")
    p_profile = await get_user_profile(req, user_id)
    mock_provider_auth_user = AuthUser(id=p_profile["id"],
                                             email=p_profile["email"],
                                             cueusername=p_profile["cueusername"],
                                             name=p_profile["name"],
                                             first_name="test",
                                             last_name="user",
                                             roles=p_profile["roles"],
                                             ngroups=[str(p_profile["ngroups"][0]["id"])],
                                             privileges=p_profile["privileges"],
                                             active_ngroup_id=str(p_profile["ngroups"][0]["id"]))
    collection2 = await seed_collection("test_collection2", True, provider_id=provider2["id"], egress_id=egress2["id"], ngroup_id=ngroup2["id"])
    file_id2 = uuid.uuid4()

    file2 = await seed_file(file_id2, "file2", 'application/octet-stream', user_id2, 1024, collection_id=collection2["id"], status="distributed")
    #Admin able to access outside of associated ngroup 
    await check_user_access_to_file(req, test_admin_user, file_id2)

    #Provider not able to access out of associated ngroup
    with pytest.raises(HTTPException):
        await check_user_access_to_file(req, mock_provider_auth_user, file_id2)

@pytest.mark.asyncio
async def test_check_user_access_to_file_not_found(make_request, seed_user):
    req = make_request()
    file_id = uuid.uuid4()

    role_id="ef872fe7-92b9-45ec-ac19-80f4c478fd36" 
    user_id = uuid.uuid4()
    await seed_user(user_id, "test_email@test.com", "test_username_user", "test_user", role_id)
    dm_profile = await get_user_profile(req, user_id)
    mock_daac_manager_auth_user = AuthUser(id=dm_profile["id"],
                                           email=dm_profile["email"],
                                           cueusername=dm_profile["cueusername"],
                                           name=dm_profile["name"],
                                           roles=dm_profile["roles"],
                                           ngroups=[str(dm_profile["ngroups"][0]["id"])],
                                           privileges=dm_profile["privileges"],
                                           active_ngroup_id=str(dm_profile["ngroups"][0]["id"]))
    with pytest.raises(HTTPException):
        await check_user_access_to_file(req, mock_daac_manager_auth_user, file_id)

@pytest.mark.asyncio
async def test_check_user_access_to_file_ngroups_dict(make_request, seed_file, seed_user, test_admin_user):
    req = make_request()
    file_id = uuid.uuid4()
    role_id="ef872fe7-92b9-45ec-ac19-80f4c478fd36" 
    user_id = uuid.uuid4()

    await seed_file(file_id, "file", 'application/octet-stream', test_admin_user.id, 1024, status="distributed")
    await seed_user(user_id, "test_email@test.com", "test_username_user", "test_user", role_id)
    dm_profile = await get_user_profile(req, user_id)
    mock_daac_manager_auth_user = AuthUser(id=dm_profile["id"],
                                           email=dm_profile["email"],
                                           cueusername=dm_profile["cueusername"],
                                           name=dm_profile["name"],
                                           roles=dm_profile["roles"],
                                           ngroups=[str(dm_profile["ngroups"][0]["id"])],
                                           privileges=dm_profile["privileges"],
                                           active_ngroup_id=str(dm_profile["ngroups"][0]["id"]))

    mock_daac_manager_auth_user.ngroups=[{"id":str(dm_profile["ngroups"][0]["id"])}]

    await check_user_access_to_file(req, mock_daac_manager_auth_user, file_id)