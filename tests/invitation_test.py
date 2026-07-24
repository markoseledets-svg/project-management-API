import pytest

@pytest.mark.asyncio
async def test_invite_user_to_project(test_client, auth_cookies, test_project_user, test_project_id):
    invitation_data = {"email":test_project_user["email"], "user_role":"admin"}
    invite_response = await test_client.post(
        f"/api/v1/projects/send-invitation/{test_project_id}",
        cookies=auth_cookies,
        json=invitation_data
    )
    assert invite_response.status_code == 201

@pytest.mark.asyncio
async def test_get_project_invites(test_client, test_project_id, auth_cookies):
    invitations_response = await test_client.get(
        f"/api/v1/projects/invitations-dashboard/{test_project_id}",
        cookies=auth_cookies
        )
    assert invitations_response.status_code == 200
    assert invitations_response.json() is not None

@pytest.mark.asyncio
async def test_get_user_invites(test_client, project_user_cookies):
    invitations_response = await test_client.get(
        f"/api/v1/projects/invitations/",
        cookies=project_user_cookies
    )
    assert invitations_response.status_code == 200
    assert invitations_response.json() is not None

@pytest.mark.asyncio
async def test_revoke_invitation(test_client, test_project_id, auth_cookies, test_project_user):
    invitation_id_response = await test_client.get(
        f"/api/v1/projects/invitations-dashboard/{test_project_id}",
        cookies = auth_cookies
        )
    assert invitation_id_response.status_code == 200

    invitation_id = [i['invitation_public_id'] for i in invitation_id_response.json() 
                    if i['invited_user_email'] == test_project_user['email']
                    and i['status'] == 'pending']

    revoke_response = await test_client.patch(
        f"/api/v1/projects/revoke-invitation/{test_project_id}/{invitation_id[0]}",
        cookies=auth_cookies
    )
    assert revoke_response.status_code == 204

@pytest.mark.asyncio
async def test_reject_invitation(test_client, project_user_cookies, test_project_id, test_project_user, auth_cookies):
    invitation_data = {"email":test_project_user["email"], "user_role":"admin"}
    invite_response = await test_client.post(
        f"/api/v1/projects/send-invitation/{test_project_id}",
        cookies=auth_cookies,
        json=invitation_data
    )
    assert invite_response.status_code == 201

    invitation_id_response = await test_client.get(
        f"/api/v1/projects/invitations-dashboard/{test_project_id}",
        cookies = auth_cookies
        )
    assert invitation_id_response.status_code == 200

    invitation_id = [i['invitation_public_id'] for i in invitation_id_response.json() 
                    if i['invited_user_email'] == test_project_user['email']
                    and i['status'] == 'pending']
    revoke_response = await test_client.patch(
        f"/api/v1/projects/reject-invitation/{invitation_id[0]}",
        cookies=project_user_cookies
    )
    assert revoke_response.status_code == 204

@pytest.mark.asyncio
async def test_send_invitation_with_owner_role(test_client, auth_cookies, test_project_user, test_project_id):
    invitation_data = {"email":test_project_user["email"], "user_role":"owner"}
    invite_response = await test_client.post(
        f"/api/v1/projects/send-invitation/{test_project_id}",
        cookies=auth_cookies,
        json=invitation_data
    )
    assert invite_response.status_code == 403

@pytest.mark.asyncio
async def test_accept_invitation(test_client, test_project_user, project_user_cookies, test_project_id, auth_cookies):
    invitation_data = {"email":test_project_user["email"], "user_role":"admin"}
    invite_response = await test_client.post(
        f"/api/v1/projects/send-invitation/{test_project_id}",
        cookies=auth_cookies,
        json=invitation_data
    )
    assert invite_response.status_code == 201

    invitation_id_response = await test_client.get(
        f"/api/v1/projects/invitations-dashboard/{test_project_id}",
        cookies = auth_cookies
        )
    assert invitation_id_response.status_code == 200

    invitation_id = [i['invitation_public_id'] for i in invitation_id_response.json() 
                    if i['invited_user_email'] == test_project_user['email']
                    and i['status'] == 'pending']
    accept_response = await test_client.patch(
        f"/api/v1/projects/accept-invitation/{invitation_id[0]}",
        cookies = project_user_cookies
    )
    assert accept_response.status_code == 204

@pytest.mark.asyncio
async def test_accept_accepted_invitation(test_client, project_user_cookies, test_project_id, auth_cookies, test_project_user):
    invitation_id_response = await test_client.get(
        f"/api/v1/projects/invitations-dashboard/{test_project_id}",
        cookies = auth_cookies
        )
    assert invitation_id_response.status_code == 200

    invitation_id = [i['invitation_public_id'] for i in invitation_id_response.json() 
                    if i['invited_user_email'] == test_project_user['email']
                    and i['status'] == 'accepted']
    
    accept_response = await test_client.patch(
        f"/api/v1/projects/accept-invitation/{invitation_id[0]}",
        cookies = project_user_cookies
    )
    assert accept_response.status_code == 409