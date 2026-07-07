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
    assert add_response.status_code == 200

@pytest.mark.asyncio
async def test_get_projects(test_client, auth_cookies):
    get_response = await test_client.get(
        "/api/v1/projects/",
       cookies=auth_cookies
    )
    assert get_response.status_code == 200
    project_list = get_response.json()
    assert len(project_list) > 0

@pytest.mark.asyncio
async def test_project_update(test_client, auth_cookies, test_project_id):
    update_data = {"project_name":"project_updated"}
    patch_response = await test_client.patch(
        f"/api/v1/projects/update/{test_project_id}",
        json=update_data,
        cookies=auth_cookies
    )
    assert patch_response.status_code == 200
    project_data = patch_response.json()
    assert project_data.get("project_name") == "project_updated"


@pytest.mark.asyncio
async def test_user_add_to_project(test_client, auth_cookies, test_project_id):
    new_relation_data = {"email":"test1@gmail.com", "user_role":"editor"}
    post_relation_request = await test_client.post(
        f"/api/v1/projects/add-user/{test_project_id}",
        json=new_relation_data,
        cookies=auth_cookies
    )
    assert post_relation_request.status_code == 200


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
async def test_invalid_access_token(test_client, test_project_id):
    fake_token_data = {"access_token": "fake.jwt.token"}
    delete_response = await test_client.delete(
        f"/api/v1/projects/delete/{test_project_id}",
        cookies=fake_token_data
    )
    assert delete_response.status_code == 401


@pytest.mark.asyncio
async def test_project_delete(test_client, auth_cookies, test_project_id):
    delete_response = await test_client.delete(
        f"/api/v1/projects/delete/{test_project_id}",
        cookies=auth_cookies
    )
    assert delete_response.status_code == 200

@pytest.mark.asyncio
async def test_deleted_project_error(test_client, auth_cookies, test_project_id):
    update_data = {"project_name":"project_soft_deleted"}
    response = await test_client.patch(
        f"/api/v1/projects/update/{test_project_id}",
        json=update_data,
        cookies=auth_cookies
    )
    assert response.status_code == 410
