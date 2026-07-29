import pytest
import uuid6

@pytest.mark.asyncio
async def test_add_new_project(test_client, auth_cookies):
    project_data = {"project_name":"new_project"}
    add_response = await test_client.post(
        "/api/v1/projects/add",
       cookies=auth_cookies,
        json=project_data
    )
    assert add_response.status_code == 201

@pytest.mark.asyncio
async def test_get_projects(test_client, auth_cookies, test_project):
    get_response = await test_client.get(
        "/api/v1/projects/",
       cookies=auth_cookies
    )
    assert get_response.status_code == 200
    project_list = get_response.json()
    assert len(project_list) > 0

@pytest.mark.asyncio
async def test_project_update(test_client, auth_cookies, test_project):
    update_data = {"project_name":"project_updated"}
    patch_response = await test_client.patch(
        f"/api/v1/projects/update/{test_project.project_public_id}",
        json=update_data,
        cookies=auth_cookies
    )
    assert patch_response.status_code == 200
    project_data = patch_response.json()
    assert project_data.get("project_name") == "project_updated"

@pytest.mark.asyncio
async def test_get_project_members(test_client, auth_cookies, test_project):
    get_response = await test_client.get(
        f"/api/v1/projects/members/{test_project.project_public_id}",
        cookies=auth_cookies
    )
    assert get_response.status_code == 200
    assert get_response.json() is not None

@pytest.mark.asyncio
async def test_change_role_to_owner(test_client, auth_cookies, test_project, test_project_member):
    new_role_data = {"user_public_id": str(test_project_member.user_public_id), "user_role": 'owner'}
    update_response = await test_client.patch(
        f"/api/v1/projects/change-role/{test_project.project_public_id}",
        json=new_role_data,
        cookies=auth_cookies
    )
    assert update_response.status_code == 403

@pytest.mark.asyncio
async def test_change_user_role(test_client, auth_cookies, test_project, test_project_member):
    new_role_data = {"user_public_id": str(test_project_member.user_public_id), "user_role": 'editor'}
    update_response = await test_client.patch(
        f"/api/v1/projects/change-role/{test_project.project_public_id}",
        json=new_role_data,
        cookies=auth_cookies
    )
    assert update_response.status_code == 204

@pytest.mark.asyncio
async def test_owner_leave_from_project(test_client, test_project, auth_cookies, test_project_member):
    leave_response = await test_client.post(
        f"/api/v1/projects/leave/{test_project.project_public_id}",
        cookies=auth_cookies
        )
    assert leave_response.status_code == 409

@pytest.mark.asyncio
async def test_assign_new_owner(test_client, test_project, auth_cookies, test_project_member):
    assign_response = await test_client.patch(
        f"/api/v1/projects/reassign-owner/{test_project.project_public_id}/{test_project_member.user_public_id}",
        cookies=auth_cookies
    )
    assert assign_response.status_code == 204

@pytest.mark.asyncio
async def test_user_leave_from_project(test_client, auth_cookies, test_project):
    
    leave_response = await test_client.post(
        f"/api/v1/projects/leave/{test_project.project_public_id}",
        cookies=auth_cookies
        )
    assert leave_response.status_code == 204

@pytest.mark.asyncio
async def test_project_not_found(test_client, auth_cookies):
    update_data = {"project_name":"no_project_exists"}
    project_id = uuid6.uuid7()
    response = await test_client.patch(
        f"/api/v1/projects/update/{project_id}",
        json=update_data,
        cookies=auth_cookies
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_invalid_access_token(test_client, test_project):
    fake_token_data = {"access_token": "fake.jwt.token"}
    delete_response = await test_client.delete(
        f"/api/v1/projects/delete/{test_project.project_public_id}",
        cookies=fake_token_data
    )
    assert delete_response.status_code == 401

@pytest.mark.asyncio
async def test_deletion_process(test_client, auth_cookies, test_project):
    
    soft_delete_response = await test_client.delete(
        f"/api/v1/projects/delete/{test_project.project_public_id}",
        cookies=auth_cookies
    )
    assert soft_delete_response.status_code == 200

    hard_delete_response = await test_client.request(
        "DELETE",
        f"/api/v1/projects/hard-delete/{test_project.project_public_id}",
        json={"project_name":test_project.project_name},
        cookies=auth_cookies
    )
    assert hard_delete_response.status_code == 204

@pytest.mark.asyncio
async def test_user_self_delete(test_client, auth_cookies, test_project, test_project_member):

    
    delete_user_response = await test_client.delete(
       f"/api/v1/projects/delete-member/{test_project.project_public_id}/{test_project_member.user_public_id}",
        cookies = auth_cookies
    )
    assert delete_user_response.status_code == 204
