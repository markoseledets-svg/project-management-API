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
    response_data = get_response.json()
    assert len(response_data['items']) > 0
    assert response_data['has_prev'] == response_data['has_next'] == False

@pytest.mark.asyncio
async def test_get_pagination_response(test_client, auth_cookies):
    get_response = await test_client.get(
        "/api/v1/projects/?page=2&limit=10",
        cookies=auth_cookies
    )
    assert get_response.status_code == 200
    response_data = get_response.json()
    assert response_data['page'] == 2
    assert response_data['limit'] == 10
    assert isinstance(response_data['items'], list)

@pytest.mark.asyncio
async def test_get_empty_pagination_response(test_client, auth_cookies):
    get_response = await test_client.get(
        "/api/v1/projects/",
       cookies=auth_cookies
    )
    assert get_response.status_code == 200
    response_data = get_response.json()
    assert isinstance(response_data['items'], list)
    assert response_data['has_prev'] == response_data['has_next'] == False

@pytest.mark.asyncio
async def test_invalid_pagination_params(test_client, auth_cookies):
    invalid_limit = await test_client.get(
        "/api/v1/projects/?page=1&limit=99999",
       cookies=auth_cookies
    )
    invalid_page = await test_client.get(
        "/api/v1/projects/?page=0&limit=20",
       cookies=auth_cookies
    )
    assert invalid_limit.status_code == invalid_page.status_code == 422



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
    response_data = get_response.json()
    assert isinstance(response_data['items'], list)
    assert len(response_data['items']) > 0
    assert response_data['page'] == 1

@pytest.mark.asyncio
async def test_project_members_invalid_pagination(test_client, auth_cookies, test_project):
    invalid_limit = await test_client.get(
        f"/api/v1/projects/members/{test_project.project_public_id}?page=1&limit=99999",
        cookies=auth_cookies
    )
    invalid_page = await test_client.get(
        f"/api/v1/projects/members/{test_project.project_public_id}?page=0&limit=20",
        cookies=auth_cookies
    )
    assert invalid_limit.status_code == invalid_page.status_code == 422

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

@pytest.mark.asyncio
async def test_sort_projects_by_name(test_client, auth_cookies, sort_projects):
    res_asc = await test_client.get("/api/v1/projects/?sort_by=project_name&sort_order=asc", cookies=auth_cookies)
    assert res_asc.status_code == 200
    names_asc = [p["project_name"] for p in res_asc.json()["items"]]
    assert names_asc == sorted(names_asc)

    res_desc = await test_client.get("/api/v1/projects/?sort_by=project_name&sort_order=desc", cookies=auth_cookies)
    assert res_desc.status_code == 200
    names_desc = [p["project_name"] for p in res_desc.json()["items"]]
    assert names_desc == sorted(names_desc, reverse=True)

@pytest.mark.asyncio
async def test_sort_projects_invalid_params(test_client, auth_cookies):
    res_invalid_field = await test_client.get("/api/v1/projects/?sort_by=invalid_field", cookies=auth_cookies)
    assert res_invalid_field.status_code == 422

    res_invalid_order = await test_client.get("/api/v1/projects/?sort_order=invalid_order", cookies=auth_cookies)
    assert res_invalid_order.status_code == 422

