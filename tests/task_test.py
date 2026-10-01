import pytest
import uuid6

@pytest.mark.asyncio
async def test_add_new_task(test_client, test_project, auth_cookies):
    task_data = {"task_name":"new_task", "description":"new_task_description"}
    task_response = await test_client.post(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/",
        json=task_data,
        cookies=auth_cookies
    )
    assert task_response.status_code == 201

@pytest.mark.asyncio
async def test_add_empty_task(test_client, test_project, auth_cookies):
    task_data = {}
    task_response = await test_client.post(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/",
        json=task_data,
        cookies=auth_cookies
    )
    assert task_response.status_code == 422

@pytest.mark.asyncio
async def test_get_user_tasks(test_client, test_project, auth_cookies, test_task):
    get_tasks_response = await test_client.get(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/",
        cookies=auth_cookies
    )
    assert get_tasks_response.status_code == 200
    response_data = get_tasks_response.json()
    assert isinstance(response_data['items'], list)
    assert len(response_data['items']) > 0
    assert response_data['has_prev'] == response_data['has_next'] == False

@pytest.mark.asyncio
async def test_get_tasks_pagination_response(test_client, test_project, auth_cookies, test_task):
    get_tasks_response = await test_client.get(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/?page=2&limit=10",
        cookies=auth_cookies
    )
    assert get_tasks_response.status_code == 200
    response_data = get_tasks_response.json()
    assert response_data['page'] == 2
    assert response_data['limit'] == 10
    assert isinstance(response_data['items'], list)

@pytest.mark.asyncio
async def test_invalid_tasks_pagination_params(test_client, test_project, auth_cookies):
    invalid_limit = await test_client.get(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/?page=1&limit=99999",
        cookies=auth_cookies
    )
    invalid_page = await test_client.get(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/?page=0&limit=20",
        cookies=auth_cookies
    )
    assert invalid_limit.status_code == invalid_page.status_code == 422

@pytest.mark.asyncio
async def test_task_update(test_client, test_project, auth_cookies, test_task):
    update_model = {"task_name":"new_task_name", "description":"task_descreption_update"}
    get_tasks_response = await test_client.patch(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/{test_task.task_public_id}",
        json=update_model,
        cookies=auth_cookies
    )
    assert get_tasks_response.status_code == 200

@pytest.mark.asyncio
async def test_task_update_status(test_client, test_project, auth_cookies, test_task_assignee):
    get_tasks_response = await test_client.patch(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/{test_task_assignee.task_public_id}/status/review",
        cookies=auth_cookies
    )
    assert get_tasks_response.status_code == 200

@pytest.mark.asyncio
async def test_task_delete(test_client, test_project, auth_cookies, test_task):
    get_tasks_response = await test_client.delete(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/{test_task.task_public_id}",
        cookies=auth_cookies
    )
    assert get_tasks_response.status_code == 204

@pytest.mark.asyncio
async def test_task_not_found(test_client, test_project, auth_cookies):
    public_id = uuid6.uuid7()
    get_tasks_response = await test_client.delete(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/{public_id}",
        cookies=auth_cookies
    )
    assert get_tasks_response.status_code == 404

@pytest.mark.asyncio
async def test_review_status(test_client, test_task_assignee, auth_cookies):
    review_response = await test_client.patch(
        f"/api/v1/projects/{test_task_assignee.project_public_id}/tasks/{test_task_assignee.task_public_id}/status/review",
        cookies=auth_cookies
    )
    assert review_response.status_code == 200

@pytest.mark.asyncio
async def test_cancel_review(test_client, test_task_review, auth_cookies):
    cancel_response = await test_client.patch(
        f"/api/v1/projects/{test_task_review.project_public_id}/tasks/{test_task_review.task_public_id}/status/cancel-review",
        cookies=auth_cookies
    )
    assert cancel_response.status_code == 200

@pytest.mark.asyncio
async def test_complete_task(test_client, test_task_review, auth_cookies):
    complete_response = await test_client.patch(
        f"/api/v1/projects/{test_task_review.project_public_id}/tasks/{test_task_review.task_public_id}/status/completed",
        cookies=auth_cookies
    )
    assert complete_response.status_code == 200

@pytest.mark.asyncio
async def test_cancel_completed(test_client, test_task_completed, auth_cookies):
    complete_response = await test_client.patch(
        f"/api/v1/projects/{test_task_completed.project_public_id}/tasks/{test_task_completed.task_public_id}/status/cancel-completed",
        cookies=auth_cookies
    )
    assert complete_response.status_code == 200

@pytest.mark.asyncio
async def test_assign_user(test_client, test_task, test_project_user, test_project_member, auth_cookies):
    assign_response = await test_client.patch(
        f"/api/v1/projects/{test_task.project_public_id}/tasks/{test_task.task_public_id}/assignee/{test_project_user.public_id}",
        cookies=auth_cookies
    )
    assert assign_response.status_code == 200

@pytest.mark.asyncio
async def test_delete_assignee(test_client, test_task_assignee, auth_cookies):
    assign_response = await test_client.delete(
        f"/api/v1/projects/{test_task_assignee.project_public_id}/tasks/{test_task_assignee.task_public_id}/assignee",
        cookies=auth_cookies
    )
    assert assign_response.status_code == 200

@pytest.mark.asyncio
async def test_self_assign(test_client, test_project, test_user, auth_cookies, test_unassigned_task):
    assign_response = await test_client.post(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/{test_unassigned_task.task_public_id}/self-assign",
        cookies=auth_cookies
    )
    assert assign_response.status_code == 200

@pytest.mark.asyncio
async def test_skip_status_todo_to_completed(test_client, test_project, auth_cookies, test_unassigned_task):
    resp = await test_client.patch(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/{test_unassigned_task.task_public_id}/status/completed",
        cookies=auth_cookies
    )
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_assign_on_review_task_blocked(test_client, test_task_assignee, test_project_user, test_project_member, auth_cookies):
    await test_client.patch(
        f"/api/v1/projects/{test_task_assignee.project_public_id}/tasks/{test_task_assignee.task_public_id}/status/review",
        cookies=auth_cookies
    )
    resp = await test_client.patch(
        f"/api/v1/projects/{test_task_assignee.project_public_id}/tasks/{test_task_assignee.task_public_id}/assignee/{test_project_user.public_id}",
        cookies=auth_cookies
    )
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_self_assign_already_taken(test_client, test_project, auth_cookies, test_task_assignee):
    resp = await test_client.post(
        f"/api/v1/projects/{test_task_assignee.project_public_id}/tasks/{test_task_assignee.task_public_id}/self-assign",
        cookies=auth_cookies
    )
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_sort_tasks_by_name(test_client, test_project, auth_cookies, sort_tasks):
    res_asc = await test_client.get(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/?sort_by=task_name&sort_order=asc",
        cookies=auth_cookies
    )
    assert res_asc.status_code == 200
    names_asc = [t["task_name"] for t in res_asc.json()["items"]]
    assert names_asc == sorted(names_asc)

    res_desc = await test_client.get(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/?sort_by=task_name&sort_order=desc",
        cookies=auth_cookies
    )
    assert res_desc.status_code == 200
    names_desc = [t["task_name"] for t in res_desc.json()["items"]]
    assert names_desc == sorted(names_desc, reverse=True)

@pytest.mark.asyncio
async def test_sort_tasks_invalid_params(test_client, test_project, auth_cookies):
    res_invalid_field = await test_client.get(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/?sort_by=invalid_field",
        cookies=auth_cookies
    )
    assert res_invalid_field.status_code == 422

    res_invalid_order = await test_client.get(
        f"/api/v1/projects/{test_project.project_public_id}/tasks/?sort_order=invalid_order",
        cookies=auth_cookies
    )
    assert res_invalid_order.status_code == 422