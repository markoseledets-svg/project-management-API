import pytest
from unittest.mock import AsyncMock

from schemas.login_schemas import UserGetModel


@pytest.mark.asyncio
async def test_cache_set_and_get(test_user, fake_redis, test_redis_services, mock_loader):
    cache_miss = await test_redis_services.get_or_set_cache(
        f'user:{test_user.public_id}',
        UserGetModel,
        mock_loader,
        900
    )
    assert isinstance(cache_miss, UserGetModel)
    assert await fake_redis.get(f'cache:user:{test_user.public_id}') is not None

    cache_hit = await test_redis_services.get_or_set_cache(
        f'user:{test_user.public_id}',
        UserGetModel,
        mock_loader,
        900
    )
    assert isinstance(cache_hit, UserGetModel)
    assert mock_loader.call_count == 1


@pytest.mark.asyncio
async def test_cache_invalidation(user_cache, fake_redis, test_redis_services):
    key = f'cache:user:{user_cache.public_id}'
    assert await fake_redis.get(key) is not None
    await test_redis_services.invalidate_cache(key)
    assert await fake_redis.get(key) is None


@pytest.mark.asyncio
async def test_none_data_caching(fake_redis, test_redis_services):
    loader = AsyncMock(return_value=None)
    none_caching = await test_redis_services.get_or_set_cache(
        'user:uid',
        UserGetModel,
        loader,
        900
    )
    assert none_caching is None
    assert await fake_redis.get('cache:user:uid') is None


@pytest.mark.asyncio
async def test_versioning(fake_redis, test_redis_services):
    ver = await test_redis_services.get_version('ver_key')
    assert ver == 0
    await test_redis_services.bump_version('ver_key')
    assert await fake_redis.get('cache:ver_key') == '1'
    await test_redis_services.bump_version('ver_key')
    assert await fake_redis.get('cache:ver_key') == '2'


@pytest.mark.asyncio
async def test_redis_error_while_caching(redis_error, test_redis_services, user_cache, mock_loader):
    user_data = await test_redis_services.get_or_set_cache(
        f'user:{user_cache.public_id}',
        UserGetModel,
        mock_loader,
        900
    )
    assert user_data is not None
    assert isinstance(user_data, UserGetModel)


@pytest.mark.asyncio
async def test_api_user_cache_flow(test_client, auth_cookies, test_user, fake_redis):
    cache_key = f'cache:user:{test_user.public_id}'
    assert await fake_redis.get(cache_key) is None

    response = await test_client.get('/api/v1/auth/me', cookies=auth_cookies)
    assert response.status_code == 200
    assert await fake_redis.get(cache_key) is not None

    delete_response = await test_client.delete('/api/v1/auth/delete-account', cookies=auth_cookies)
    assert delete_response.status_code == 204
    assert await fake_redis.get(cache_key) is None


@pytest.mark.asyncio
async def test_api_permission_cache_flow(test_client, auth_cookies, test_user, test_project, test_project_member, fake_redis):
    owner_role_key = f'cache:user_role:{test_user.public_id}:{test_project.project_public_id}'
    member_role_key = f'cache:user_role:{test_project_member.user_public_id}:{test_project.project_public_id}'

    res = await test_client.get(f'/api/v1/projects/members/{test_project.project_public_id}', cookies=auth_cookies)
    assert res.status_code == 200
    assert await fake_redis.get(owner_role_key) == '"owner"'

    update_data = {
        "user_public_id": str(test_project_member.user_public_id),
        "user_role": "editor"
    }
    patch_res = await test_client.patch(
        f'/api/v1/projects/change-role/{test_project.project_public_id}',
        json=update_data,
        cookies=auth_cookies
    )
    assert patch_res.status_code == 204
    assert await fake_redis.get(member_role_key) is None
    assert await fake_redis.get(f'cache:project_status:{test_project.project_public_id}') == '"active"'


@pytest.mark.asyncio
async def test_api_project_status_invalidation_flow(test_client, auth_cookies, test_project, fake_redis):
    pid = test_project.project_public_id
    status_key = f'cache:project_status:{pid}'

    await fake_redis.set(status_key, '"active"')
    assert await fake_redis.get(status_key) == '"active"'

    delete_res = await test_client.delete(f'/api/v1/projects/delete/{pid}', cookies=auth_cookies)
    assert delete_res.status_code == 200
    assert await fake_redis.get(status_key) is None


@pytest.mark.asyncio
async def test_api_members_versioning_flow(test_client, auth_cookies, test_project, test_project_member, fake_redis):
    pid = test_project.project_public_id
    ver_key = f'cache:project_members_ver:{pid}'

    res1 = await test_client.get(f'/api/v1/projects/members/{pid}', cookies=auth_cookies)
    assert res1.status_code == 200
    v0_cache_key = f'cache:project_members:{pid}:v0:1:20'
    assert await fake_redis.get(v0_cache_key) is not None

    update_data = {
        "user_public_id": str(test_project_member.user_public_id),
        "user_role": "editor"
    }
    patch_res = await test_client.patch(
        f'/api/v1/projects/change-role/{pid}',
        json=update_data,
        cookies=auth_cookies
    )
    assert patch_res.status_code == 204
    assert await fake_redis.get(ver_key) == '1'

    res2 = await test_client.get(f'/api/v1/projects/members/{pid}', cookies=auth_cookies)
    assert res2.status_code == 200
    v1_cache_key = f'cache:project_members:{pid}:v1:1:20'
    assert await fake_redis.get(v1_cache_key) is not None

    members = res2.json()['items']
    target_member = next(m for m in members if m['public_id'] == str(test_project_member.user_public_id))
    assert target_member['user_role'] == 'editor'


@pytest.mark.asyncio
async def test_api_invitation_acceptance_versioning_flow(test_client, project_user_cookies, test_invitation, fake_redis):
    pid = test_invitation.project_public_id
    ver_key = f'cache:project_members_ver:{pid}'

    assert await fake_redis.get(ver_key) is None

    accept_res = await test_client.patch(
        f'/api/v1/projects/accept-invitation/{test_invitation.invitation_public_id}',
        cookies=project_user_cookies
    )
    assert accept_res.status_code == 204
    assert await fake_redis.get(ver_key) == '1'
