import pytest
import uuid6

@pytest.mark.asyncio
async def test_add_new_task(test_client, test_project_id, auth_headers):
    task_data = {"task_name":"new_task", "description":"new_task_description"}
    task_response = await test_client.post(
        f"/api/v1/projects/{test_project_id}/tasks/",
        json=task_data,
        headers=auth_headers
    )
    assert task_response.status_code == 200

@pytest.mark.asyncio
async def test_add_empty_task(test_client, test_project_id, auth_headers):
    task_data = {}
    task_response = await test_client.post(
        f"/api/v1/projects/{test_project_id}/tasks/",
        json=task_data,
        headers=auth_headers
    )
    assert task_response.status_code == 422

@pytest.mark.asyncio
async def test_get_user_tasks(test_client, test_project_id, auth_headers):
    get_tasks_response = await test_client.get(
        f"/api/v1/projects/{test_project_id}/tasks/",
        headers=auth_headers
    )
    assert get_tasks_response.status_code == 200

@pytest.mark.asyncio
async def test_task_update(test_client, test_project_id, auth_headers, test_task_id):
    update_model = {"task_name":"new_task_name", "description":"task_descreption_update"}
    get_tasks_response = await test_client.patch(
        f"/api/v1/projects/{test_project_id}/tasks/{test_task_id}",
        json=update_model,
        headers=auth_headers
    )
    assert get_tasks_response.status_code == 200

@pytest.mark.asyncio
async def test_task_update_status(test_client, test_project_id, auth_headers, test_task_id):
    get_tasks_response = await test_client.patch(
        f"/api/v1/projects/{test_project_id}/tasks/{test_task_id}/change-status",
        headers=auth_headers
    )
    assert get_tasks_response.status_code == 200

@pytest.mark.asyncio
async def test_task_delete(test_client, test_project_id, auth_headers, test_task_id):
    get_tasks_response = await test_client.delete(
        f"/api/v1/projects/{test_project_id}/tasks/{test_task_id}",
        headers=auth_headers
    )
    assert get_tasks_response.status_code == 200

@pytest.mark.asyncio
async def test_task_not_found(test_client, test_project_id, auth_headers):
    public_id = uuid6.uuid7()
    get_tasks_response = await test_client.delete(
        f"/api/v1/projects/{test_project_id}/tasks/{public_id}",
        headers=auth_headers
    )
    assert get_tasks_response.status_code == 404
