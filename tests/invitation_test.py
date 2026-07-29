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
    assert invitations_response.json() is not False

@pytest.mark.asyncio
async def test_get_user_invites(test_client, project_user_cookies):
    invitations_response = await test_client.get(
        f"/api/v1/projects/invitations/",
        cookies=project_user_cookies
    )
    assert invitations_response.status_code == 200
    assert invitations_response.json() is not False

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

    