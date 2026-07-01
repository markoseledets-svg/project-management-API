import pytest

@pytest.mark.asyncio
async def test_registration(test_client):
    user_data = {"email":"test1@gmail.com", "password":"password123"}
    succesfull_response = await test_client.post(
                                    "/api/v1/auth/register",
                                    json = user_data
                                    )
    assert succesfull_response.status_code == 200

@pytest.mark.asyncio
async def test_duplicate_email(test_client, test_user):
    duplicate_error_response = await test_client.post(
                                        "/api/v1/auth/register",
                                        json = test_user
                                    )
    assert duplicate_error_response.status_code == 409


#need to be rewrited for new tokens algo
@pytest.mark.asyncio
async def test_auth_and_refresh(test_client, test_user):
    user_data = {"username": test_user["email"], "password": test_user["password"]}
    succesfull_login_response = await test_client.post(
        "/api/v1/auth/",
        data = user_data
    )
    assert succesfull_login_response.status_code == 200
    token = succesfull_login_response.json()["refresh_token"]
    refresh_rotation_request = await test_client.post(
        "/api/v1/auth/refresh",
        json = {"refresh_token":token}
    )
    assert refresh_rotation_request.status_code == 200

@pytest.mark.asyncio
async def test_failed_login(test_client, test_user):
    user_data = {"username": test_user["email"], "password": "random_password"}
    fail_response = await test_client.post(
        "/api/v1/auth/",
        data = user_data
    )
    assert fail_response.status_code == 401

@pytest.mark.asyncio
async def test_user_not_found(test_client):
    user_data = {"username":"random@user.com", "password":"random_password"}
    not_found_response = await test_client.post(
        "/api/v1/auth/",
        data = user_data
    )
    assert not_found_response.status_code == 401

@pytest.mark.asyncio
async def test_fake_token(test_client):
    fake_token = "fake_tokena_string_123"
    response = await test_client.post("/api/v1/auth/refresh", json={"refresh_token":fake_token})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_current_user(test_client, auth_headers):
    user_response = await test_client.get(
        "/api/v1/auth/me",
        headers = auth_headers
    )
    assert user_response.status_code == 200