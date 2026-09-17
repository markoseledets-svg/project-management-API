import pytest
import json
import asyncio
import uuid6
from datetime import datetime, timedelta, timezone
from authlib.integrations.base_client import OAuthError

from database.db_model import RegistrationIdentity
from tests.factories.users import RAW_PASSWORD, RefreshFactory, AuthIdentityFactory
from core.security import generate_access_jwt, generate_refresh_jwt

@pytest.mark.asyncio
async def test_registration_process(test_client, fake_redis):
    user_data = {"email":"test1@gmail.com", "password":"Password123!"}
    succesfull_response = await test_client.post(
                                    "/api/v1/auth/register",
                                    json = user_data
                                    )
    assert succesfull_response.status_code == 200

    redis_data_str = await fake_redis.get("otp:register:test1@gmail.com")
    assert redis_data_str is not None
    redis_data = json.loads(redis_data_str)
    correct_otp = redis_data["otp"]
    code_payload = {"email":"test1@gmail.com", "otp":correct_otp}
    correct_otp_input = await test_client.post(
        "/api/v1/auth/verify-otp",
        json=code_payload
    )
    assert correct_otp_input.status_code == 201

@pytest.mark.asyncio
async def test_duplicate_email(test_client, test_user):
    payload = {'email':test_user.email, 'password':RAW_PASSWORD}
    duplicate_response = await test_client.post(
                                        "/api/v1/auth/register",
                                        json = payload
                                    )
    assert duplicate_response.status_code == 409
    
@pytest.mark.asyncio
async def test_auth(test_client, test_user, test_local_identity):
    user_data = {"username": test_user.email, "password": RAW_PASSWORD}
    succesfull_login_response = await test_client.post(
        "/api/v1/auth/",
        data = user_data
    )
    assert succesfull_login_response.status_code == 204

@pytest.mark.asyncio
async def test_refresh(test_client, test_refresh_token):
    token_cookie = {"refresh_token": test_refresh_token}
    refresh_rotation_request = await test_client.post(
        "/api/v1/auth/refresh",
        cookies=token_cookie
    )
    assert refresh_rotation_request.status_code == 204

@pytest.mark.asyncio
async def test_failed_login(test_client, test_user, test_local_identity):
    user_data = {"username": test_user.email, "password": "Random_password123"}
    fail_response = await test_client.post(
        "/api/v1/auth/",
        data = user_data
    )
    assert fail_response.status_code == 401

@pytest.mark.asyncio
async def test_user_not_found(test_client):
    user_data = {"username":"random@user.com", "password":"Random_password123"}
    not_found_response = await test_client.post(
        "/api/v1/auth/",
        data = user_data
    )
    assert not_found_response.status_code == 401

@pytest.mark.asyncio
async def test_fake_token(test_client):
    fake_token = "fake_tokena_string_123"
    response = await test_client.post(
                                        "/api/v1/auth/refresh",
                                        cookies={"refresh_token":fake_token}
                                    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_current_user(test_client, auth_cookies):
    user_response = await test_client.get(
        "/api/v1/auth/me",
        cookies = auth_cookies
    )
    assert user_response.status_code == 200

@pytest.mark.asyncio
async def test_logout_and_token_invalidation(test_client, auth_cookies):
    
    logout_request = await test_client.post(
        "/api/v1/auth/logout",
        cookies=auth_cookies
    )
    assert logout_request.status_code == 204
    test_access_blacklist = await test_client.get(
        "/api/v1/auth/me",
        cookies=auth_cookies
    )
    assert test_access_blacklist.status_code == 401
    test_refresh_record_deleted = await test_client.post(
        "/api/v1/auth/refresh",
        cookies=auth_cookies
    )
    assert test_refresh_record_deleted.status_code == 401

@pytest.mark.asyncio
async def test_rate_limit(test_client):
    bad_user_data = {"username":"user@mail.fake", "password":"Userfake123_"}
    statuses = []
    for _ in range(6):
        response = await test_client.post(
            "/api/v1/auth/",
            data=bad_user_data
        )
        statuses.append(response.status_code)
    assert statuses == [401, 401, 401, 401, 401, 429]

@pytest.mark.asyncio
async def test_token_retry_and_reuse(test_client, test_refresh_token):
    token_cookie = {"refresh_token": test_refresh_token}
    refresh_request = await test_client.post(
            "/api/v1/auth/refresh",
            cookies=token_cookie
        )
    assert refresh_request.status_code == 204
    retry_request = await test_client.post(
            "/api/v1/auth/refresh",
            cookies=token_cookie
        )
    assert retry_request.status_code == 204

    new_refresh_cookies =  {"refresh_token": retry_request.cookies.get("refresh_token")}
    await asyncio.sleep(5)
    reuse_request = await test_client.post(
            "/api/v1/auth/refresh",
            cookies=token_cookie
        )
    assert reuse_request.status_code == 401
    family_banned_request = await test_client.post(
            "/api/v1/auth/refresh",
            cookies=new_refresh_cookies
        )
    assert family_banned_request.status_code == 401

@pytest.mark.asyncio
async def test_get_active_sessions(test_client, auth_cookies):
    response = await test_client.get(
        "/api/v1/auth/active-sessions",
        cookies=auth_cookies
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert "token_public_id" in data[0]
    assert "session_started_at" in data[0]

@pytest.mark.asyncio
async def test_active_sessions_filters_expired(test_client, test_user, auth_cookies):
    await RefreshFactory.create_async(
        user_public_id=test_user.public_id,
        expired_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    response = await test_client.get(
        "/api/v1/auth/active-sessions",
        cookies=auth_cookies
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

@pytest.mark.asyncio
async def test_logout_session_success(test_client, test_user, auth_cookies):
    second_refresh = await RefreshFactory.create_async(user_public_id=test_user.public_id)
    second_access = generate_access_jwt(test_user.public_id, second_refresh.family_id)
    second_refresh_jwt = generate_refresh_jwt(test_user.public_id, second_refresh.token_public_id)

    logout_response = await test_client.post(
        f"/api/v1/auth/logout-session/{second_refresh.token_public_id}",
        cookies=auth_cookies
    )
    assert logout_response.status_code == 204

    me_response = await test_client.get(
        "/api/v1/auth/me",
        cookies={"access_token": second_access}
    )
    assert me_response.status_code == 401

    refresh_response = await test_client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": second_refresh_jwt}
    )
    assert refresh_response.status_code == 401

@pytest.mark.asyncio
async def test_logout_session_not_found(test_client, auth_cookies):
    fake_token_id = uuid6.uuid7()
    response = await test_client.post(
        f"/api/v1/auth/logout-session/{fake_token_id}",
        cookies=auth_cookies
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_logout_everywhere(test_client, test_user, auth_cookies):
    second_refresh = await RefreshFactory.create_async(user_public_id=test_user.public_id)
    second_access = generate_access_jwt(test_user.public_id, second_refresh.family_id)

    response = await test_client.post(
        "/api/v1/auth/logout-everywhere",
        cookies=auth_cookies
    )
    assert response.status_code == 204

    me_response_1 = await test_client.get(
        "/api/v1/auth/me",
        cookies=auth_cookies
    )
    assert me_response_1.status_code == 401

    me_response_2 = await test_client.get(
        "/api/v1/auth/me",
        cookies={"access_token": second_access}
    )
    assert me_response_2.status_code == 401

@pytest.mark.asyncio
async def test_delete_and_restore_account_flow(test_client, test_user, auth_cookies, test_local_identity):
    delete_response = await test_client.delete(
        "/api/v1/auth/delete-account",
        cookies=auth_cookies
    )
    assert delete_response.status_code == 204

    login_response = await test_client.post(
        "/api/v1/auth/",
        data={"username": test_user.email, "password": RAW_PASSWORD}
    )
    assert login_response.status_code == 204
    restore_token = login_response.cookies.get('restore_token')

    restore_response = await test_client.post(
        "/api/v1/auth/restore-account",
        json={"restore_token": restore_token}
    )
    assert restore_response.status_code == 204

    login_after_restore = await test_client.post(
        "/api/v1/auth/",
        data={"username": test_user.email, "password": RAW_PASSWORD}
    )
    assert login_after_restore.status_code == 204

@pytest.mark.asyncio
async def test_restore_token_reuse_rejected(test_client, test_user, auth_cookies, test_local_identity):
    await test_client.delete(
        "/api/v1/auth/delete-account",
        cookies=auth_cookies
    )
    login_response = await test_client.post(
        "/api/v1/auth/",
        data={"username": test_user.email, "password": RAW_PASSWORD}
    )
    restore_token = login_response.cookies.get('restore_token')

    first_restore = await test_client.post(
        "/api/v1/auth/restore-account",
        cookies={'restore_token':restore_token}
    )
    assert first_restore.status_code == 204

    second_restore = await test_client.post(
        "/api/v1/auth/restore-account",
        cookies={'restore_token':restore_token}
    )
    assert second_restore.status_code == 401

@pytest.mark.asyncio
async def test_change_password_flow(test_client, test_user, auth_cookies, test_local_identity):
    change_response = await test_client.post(
        "/api/v1/auth/change-password",
        cookies=auth_cookies,
        json={"old_password": RAW_PASSWORD, "password": "NewSecretPassword123!"}
    )
    assert change_response.status_code == 204

    me_response = await test_client.get(
        "/api/v1/auth/me",
        cookies=auth_cookies
    )
    assert me_response.status_code == 401

    login_new = await test_client.post(
        "/api/v1/auth/",
        data={"username": test_user.email, "password": "NewSecretPassword123!"}
    )
    assert login_new.status_code == 204

@pytest.mark.asyncio
async def test_change_password_invalid_old_password(test_client, auth_cookies):
    change_response = await test_client.post(
        "/api/v1/auth/change-password",
        cookies=auth_cookies,
        json={"old_password": "WrongPassword123!", "password": "NewSecretPassword123!"}
    )
    assert change_response.status_code == 401

@pytest.mark.asyncio
async def test_forgotten_password_flow(test_client, test_user, fake_redis, test_local_identity):
    new_pwd = "RecoveredPassword123!"
    forgot_response = await test_client.post(
        "/api/v1/auth/forgotten-password",
        json={"email": test_user.email, "password": new_pwd}
    )
    assert forgot_response.status_code == 204

    redis_data_str = await fake_redis.get(f"otp:password-change:{test_user.email}")
    assert redis_data_str is not None
    otp = json.loads(redis_data_str)["otp"]

    verify_response = await test_client.post(
        "/api/v1/auth/verify-password-change",
        json={"email": test_user.email, "otp": otp}
    )
    assert verify_response.status_code == 204

    login_response = await test_client.post(
        "/api/v1/auth/",
        data={"username": test_user.email, "password": new_pwd}
    )
    assert login_response.status_code == 204

@pytest.mark.asyncio
async def test_oauth_redirects(test_client, auth_cookies):
    auth_google_response = await test_client.get(
        '/api/v1/auth/oauth/google/auth'
    )
    assert auth_google_response.status_code == 302
    link_google_response = await test_client.get(
        '/api/v1/auth/oauth/google/link',
        cookies=auth_cookies
    )
    assert link_google_response.status_code == 302
    auth_github_response = await test_client.get(
        '/api/v1/auth/oauth/github/auth'
    )
    assert auth_github_response.status_code == 302
    link_github_response = await test_client.get(
        '/api/v1/auth/oauth/github/link',
        cookies=auth_cookies
    )
    assert link_github_response.status_code == 302

@pytest.mark.asyncio
async def test_unlink_provider(test_client, test_local_identity, test_google_identity, auth_cookies):
    delete_response = await test_client.delete(
        f'/api/v1/auth/unlink-provider/{test_google_identity.identity_public_id}',
        cookies=auth_cookies
    )
    assert delete_response.status_code == 204

@pytest.mark.asyncio
async def test_add_password(test_client, test_google_identity, auth_cookies, fake_redis):
    add_response = await test_client.post(
        '/api/v1/auth/add-password',
        json={"password": "NewStrongPassword123!"},
        cookies=auth_cookies
    )
    assert add_response.status_code == 204
    otp_redis_data = await fake_redis.get(f'otp:add-password:{test_google_identity.user_public_id}')
    assert otp_redis_data is not None
    otp = json.loads(otp_redis_data)["otp"]
    verify_response = await test_client.post(
        '/api/v1/auth/add-password/verify',
        json={"otp": otp},
        cookies=auth_cookies
    )
    assert verify_response.status_code == 204

@pytest.mark.asyncio
async def test_get_user_providers(test_client, auth_cookies, test_google_identity):
    providers_response = await test_client.get(
        '/api/v1/auth/providers',
        cookies=auth_cookies
    )
    assert providers_response.status_code == 200
    data = providers_response.json()
    assert len(data) >= 1
    assert any(p["provider"] == "google" for p in data)

@pytest.mark.asyncio
async def test_unlink_last_provider_forbidden(test_client, test_google_identity, auth_cookies):
    delete_response = await test_client.delete(
        f'/api/v1/auth/unlink-provider/{test_google_identity.identity_public_id}',
        cookies=auth_cookies
    )
    assert delete_response.status_code == 403

@pytest.mark.asyncio
async def test_unlink_local_forbidden(test_client, test_local_identity, test_google_identity, auth_cookies):
    delete_response = await test_client.delete(
        f'/api/v1/auth/unlink-provider/{test_local_identity.identity_public_id}',
        cookies=auth_cookies
    )
    assert delete_response.status_code == 403

@pytest.mark.asyncio
async def test_unlink_non_existent_provider(test_client, auth_cookies):
    random_id = uuid6.uuid7()
    delete_response = await test_client.delete(
        f'/api/v1/auth/unlink-provider/{random_id}',
        cookies=auth_cookies
    )
    assert delete_response.status_code == 404

@pytest.mark.asyncio
async def test_add_password_already_exists(test_client, test_local_identity, auth_cookies):
    response = await test_client.post(
        '/api/v1/auth/add-password',
        json={"password": "AnotherStrongPassword123!"},
        cookies=auth_cookies
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_add_password_wrong_otp(test_client, test_google_identity, auth_cookies, fake_redis):
    add_response = await test_client.post(
        '/api/v1/auth/add-password',
        json={"password": "NewStrongPassword123!"},
        cookies=auth_cookies
    )
    assert add_response.status_code == 204
    verify_response = await test_client.post(
        '/api/v1/auth/add-password/verify',
        json={"otp": 999999},
        cookies=auth_cookies
    )
    assert verify_response.status_code == 401

@pytest.mark.asyncio
async def test_google_callback_login_success(test_client, mock_google_oauth):
    mock_google_oauth.configure(email="google_new_user@test.com", sub="google-sub-12345")
    response = await test_client.get("/api/v1/auth/oauth/google/callback")
    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:8000/app"
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

@pytest.mark.asyncio
async def test_google_callback_link_success(test_client, test_user, auth_cookies, mock_google_oauth):
    mock_google_oauth.configure(email=test_user.email, sub="google-link-sub-777")
    response = await test_client.get(
        "/api/v1/auth/oauth/google/callback?state=link",
        cookies=auth_cookies
    )
    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:8000/app"

@pytest.mark.asyncio
async def test_google_callback_error(test_client, mock_google_oauth):
    mock_google_oauth.side_effect = OAuthError("access_denied", description="The user denied consent")
    response = await test_client.get("/api/v1/auth/oauth/google/callback")
    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:8000/"
    assert "oauth_error" in response.cookies

@pytest.mark.asyncio
async def test_github_callback_login_success(test_client, mock_github_oauth):
    mock_auth, _ = mock_github_oauth
    mock_auth.configure(email="github_new_user@test.com", user_id=12345678)
    response = await test_client.get("/api/v1/auth/oauth/github/callback")
    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:8000/app"
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

@pytest.mark.asyncio
async def test_github_callback_unverified_email(test_client, mock_github_oauth):
    mock_auth, _ = mock_github_oauth
    mock_auth.configure(email="unverified_gh@test.com", verified=False)
    response = await test_client.get("/api/v1/auth/oauth/github/callback")
    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:8000/"
    assert "oauth_error" in response.cookies
    assert "No verified email address" in response.cookies["oauth_error"]

@pytest.mark.asyncio
async def test_github_callback_link_success(test_client, test_user, auth_cookies, mock_github_oauth):
    mock_auth, _ = mock_github_oauth
    mock_auth.configure(email=test_user.email, user_id=999111222)
    response = await test_client.get(
        "/api/v1/auth/oauth/github/callback?state=link",
        cookies=auth_cookies
    )
    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:8000/app"

@pytest.mark.asyncio
async def test_github_callback_error(test_client, mock_github_oauth):
    mock_auth, _ = mock_github_oauth
    mock_auth.side_effect = OAuthError("access_denied", description="The user denied request")
    response = await test_client.get("/api/v1/auth/oauth/github/callback")
    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:8000/"
    assert "oauth_error" in response.cookies


