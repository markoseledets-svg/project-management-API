import pytest

@pytest.mark.asyncio
async def test_invite_user_to_project(test_client, auth_cookies, test_project_user, test_project):
    invitation_data = {"email":test_project_user.email, "user_role":"admin"}
    invite_response = await test_client.post(
        f"/api/v1/projects/send-invitation/{test_project.project_public_id}",
        cookies=auth_cookies,
        json=invitation_data
    )
    assert invite_response.status_code == 201

@pytest.mark.asyncio
async def test_get_project_invites(test_client, test_project, auth_cookies):
    invitations_response = await test_client.get(
        f"/api/v1/projects/invitations-dashboard/{test_project.project_public_id}",
        cookies=auth_cookies
        )
    assert invitations_response.status_code == 200
    data = invitations_response.json()
    assert isinstance(data['items'], list)
    assert data['page'] == 1
    assert data['has_prev'] == data['has_next'] == False

@pytest.mark.asyncio
async def test_get_user_invites(test_client, project_user_cookies):
    invitations_response = await test_client.get(
        f"/api/v1/projects/invitations/",
        cookies=project_user_cookies
    )
    assert invitations_response.status_code == 200
    data = invitations_response.json()
    assert isinstance(data['items'], list)
    assert data['page'] == 1
    assert data['has_prev'] == data['has_next'] == False

@pytest.mark.asyncio
async def test_invalid_invitation_pagination_params(test_client, test_project, auth_cookies, project_user_cookies):
    invalid_limit = await test_client.get(
        f"/api/v1/projects/invitations-dashboard/{test_project.project_public_id}?page=1&limit=99999",
        cookies=auth_cookies
    )
    invalid_page = await test_client.get(
        "/api/v1/projects/invitations/?page=0&limit=20",
        cookies=project_user_cookies
    )
    assert invalid_limit.status_code == invalid_page.status_code == 422

@pytest.mark.asyncio
async def test_revoke_invitation(test_client, test_project, auth_cookies, test_invitation):
    revoke_response = await test_client.patch(
        f"/api/v1/projects/revoke-invitation/{test_project.project_public_id}/{test_invitation.invitation_public_id}",
        cookies=auth_cookies
    )
    assert revoke_response.status_code == 204

@pytest.mark.asyncio
async def test_reject_invitation(test_client, project_user_cookies, test_invitation):
    
    revoke_response = await test_client.patch(
        f"/api/v1/projects/reject-invitation/{test_invitation.invitation_public_id}",
        cookies=project_user_cookies
    )
    assert revoke_response.status_code == 204

@pytest.mark.asyncio
async def test_send_invitation_with_owner_role(test_client, auth_cookies, test_project_user, test_project):
    invitation_data = {"email":test_project_user.email, "user_role":"owner"}
    invite_response = await test_client.post(
        f"/api/v1/projects/send-invitation/{test_project.project_public_id}",
        cookies=auth_cookies,
        json=invitation_data
    )
    assert invite_response.status_code == 403

@pytest.mark.asyncio
async def test_accept_invitation(test_client, project_user_cookies, test_invitation):
    
    accept_response = await test_client.patch(
        f"/api/v1/projects/accept-invitation/{test_invitation.invitation_public_id}",
        cookies = project_user_cookies
    )
    assert accept_response.status_code == 204

@pytest.mark.asyncio
async def test_accept_accepted_invitation(test_client, project_user_cookies, test_invitation):
    
    accept_response = await test_client.patch(
        f"/api/v1/projects/accept-invitation/{test_invitation.invitation_public_id}",
        cookies = project_user_cookies
    )
    assert accept_response.status_code == 204

    accept_accepted_response = await test_client.patch(
        f"/api/v1/projects/accept-invitation/{test_invitation.invitation_public_id}",
        cookies = project_user_cookies
    )
    assert accept_accepted_response.status_code == 409

@pytest.mark.asyncio
async def test_filter_invitations_by_status(test_client, test_project, auth_cookies, test_invitation):
    res_pending = await test_client.get(
        f"/api/v1/projects/invitations-dashboard/{test_project.project_public_id}?status=pending",
        cookies=auth_cookies
    )
    assert res_pending.status_code == 200
    data_pending = res_pending.json()
    assert len(data_pending["items"]) > 0
    assert all(i["status"] == "pending" for i in data_pending["items"])

    res_accepted = await test_client.get(
        f"/api/v1/projects/invitations-dashboard/{test_project.project_public_id}?status=accepted",
        cookies=auth_cookies
    )
    assert res_accepted.status_code == 200
    data_accepted = res_accepted.json()
    assert data_accepted["total_count"] == 0
    assert len(data_accepted["items"]) == 0

@pytest.mark.asyncio
async def test_filter_invitations_invalid_status(test_client, test_project, auth_cookies):
    res = await test_client.get(
        f"/api/v1/projects/invitations-dashboard/{test_project.project_public_id}?status=invalid_status",
        cookies=auth_cookies
    )
    assert res.status_code == 422
    