import pytest
import pytest
import json

@pytest.mark.asyncio
async def test_registration(test_client):
    user_data = {"email":"test1@gmail.com", "password":"password123"}
    succesfull_response = await test_client.post(
                                    "/api/v1/auth/register",
                                    json = user_data
                                    )
    assert succesfull_response.status_code == 200

@pytest.mark.asyncio
async def test_otp_verification(test_client,fake_redis):
    redis_data_str = await fake_redis.get("otp:users:test1@gmail.com")
    assert redis_data_str is not None
    redis_data = json.loads(redis_data_str)
    correct_otp = redis_data["otp"]
    code_payload = {"email":"test1@gmail.com", "otp":correct_otp}
    correct_otp_input = await test_client.post(
        "/api/v1/auth/verify-otp",
        json=code_payload
    )
    assert correct_otp_input.status_code == 200

@pytest.mark.asyncio
async def test_duplicate_email(test_client, test_user):
    duplicate_error_response = await test_client.post(
                                        "/api/v1/auth/register",
                                        json = test_user
                                    )
    assert duplicate_error_response.status_code == 409

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

@pytest.mark.asyncio
async def test_logout(test_client):
    user_login_data = {"username":"test1@gmail.com", "password":"password123"}
    headers_request = await test_client.post(
        "/api/v1/auth/",
        data=user_login_data
    )
    assert headers_request.status_code == 200
    token_data = headers_request.json()
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    body = {"user_refresh_token": token_data["refresh_token"]}
    logout_request = await test_client.post(
        "/api/v1/auth/logout",
        headers=headers,
        json=body
    )
    assert logout_request.status_code == 200
    test_access_blacklist = await test_client.get(
        "/api/v1/auth/me",
        headers = headers
    )
    assert test_access_blacklist.status_code == 401
    test_refresh_record_deleted = await test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_data["refresh_token"]}
    )
    assert test_refresh_record_deleted.status_code == 401

@pytest.mark.asyncio
async def test_rate_limit(test_client):
    bad_user_data = {"username":"user@mail.fake", "password":"userfake123"}
    statuses = []
    for _ in range(6):
        response = await test_client.post(
            "/api/v1/auth/",
            data=bad_user_data
        )
        statuses.append(response.status_code)
    assert statuses == [401, 401, 401, 401, 401, 429]