import pytest
import uuid6

@pytest.mark.asyncio
async def test_add_new_project(test_client, auth_headers):
    project_data = {"project_name":"new_project"}
    add_response = await test_client.post(
        "/api/v1/projects/add",
        headers=auth_headers,
        json=project_data
    )
    assert add_response.status_code == 200

@pytest.mark.asyncio
async def test_get_projects(test_client, auth_headers):
    get_response = await test_client.get(
        "/api/v1/projects/",
        headers = auth_headers
    )
    assert get_response.status_code == 200
    project_list = get_response.json()
    assert len(project_list) > 0

@pytest.mark.asyncio
async def test_project_update(test_client, auth_headers, test_project_id):
    update_data = {"project_name":"project_updated"}
    patch_response = await test_client.patch(
        f"/api/v1/projects/update/{test_project_id}",
        json=update_data,
        headers=auth_headers
    )
    assert patch_response.status_code == 200
    project_data = patch_response.json()
    assert project_data.get("project_name") == "project_updated"


@pytest.mark.asyncio
async def test_user_add_to_project(test_client, auth_headers, test_project_id):
    new_test_user = {"email":"project@editor.add", "password":"editor1234"}
    new_relation_data = {"email":"project@editor.add", "user_role":"admin"}
    await test_client.post(
        "/api/v1/auth/register",
        json=new_test_user
    )
    post_relation_request = await test_client.post(
        f"/api/v1/projects/add-user/{test_project_id}",
        json=new_relation_data,
        headers=auth_headers
    )
    assert post_relation_request.status_code == 200


@pytest.mark.asyncio
async def test_project_not_found(test_client, auth_headers):
    update_data = {"project_name":"no_project_exists"}
    project_id = uuid6.uuid7()
    response = await test_client.patch(
        f"/api/v1/projects/update/{project_id}",
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_invalid_access_token(test_client, test_project_id):
    fake_token_data = {"Authorization": f"Bearer fake.jwt.token"}
    delete_response = await test_client.delete(
        f"/api/v1/projects/delete/{test_project_id}",
        headers=fake_token_data
    )
    assert delete_response.status_code == 401


@pytest.mark.asyncio
async def test_project_delete(test_client, auth_headers, test_project_id):
    delete_response = await test_client.delete(
        f"/api/v1/projects/delete/{test_project_id}",
        headers=auth_headers
    )
    assert delete_response.status_code == 200

@pytest.mark.asyncio
async def test_deleted_project_error(test_client, auth_headers, test_project_id):
    update_data = {"project_name":"project_soft_deleted"}
    response = await test_client.patch(
        f"/api/v1/projects/update/{test_project_id}",
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 410

    
