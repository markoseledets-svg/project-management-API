import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import pytest
from httpx import AsyncClient, ASGITransport
from fakeredis import FakeAsyncRedis
from unittest.mock import patch
import json

from database.db_model import Base
from app.api.dependencies.db_dependencies import get_db
from app.api.dependencies.redis_dependencies import get_redis
from app.main import app
load_dotenv()

DB_URL = os.getenv("TEST_DATABASE_URL")

@pytest.fixture(scope='session')
async def fake_redis():
    fake_redis_client = FakeAsyncRedis(decode_responses=True)
    yield fake_redis_client
    await fake_redis_client.aclose()

@pytest.fixture(scope="session", autouse=True)
def mock_send_email():
    with patch("app.api.v1.routers.auth_routes.send_email") as mock:
        yield mock

@pytest.fixture(scope="session")
async def test_client(fake_redis):
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def get_test_db():
        async with AsyncSession(engine, ) as session:
            yield session
    
    async def get_fake_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = get_fake_redis
    app.dependency_overrides[get_db] = get_test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await engine.dispose()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    app.dependency_overrides.clear()

@pytest.fixture(scope="session")
async def test_user(test_client, fake_redis):
    user_credentials = {"email":"test@gmail.com", "password":"password123"}
    await test_client.post("/api/v1/auth/register", json=user_credentials)
    redis_data_str = await fake_redis.get("otp:users:test@gmail.com")
    redis_data = json.loads(redis_data_str)
    correct_otp = redis_data["otp"]
    code_payload = {"email":"test@gmail.com", "otp":correct_otp}
    await test_client.post(
        "/api/v1/auth/verify-otp",
        json=code_payload
    )
    return user_credentials

@pytest.fixture(scope="session")
async def auth_cookies(test_client, test_user):
    response = await test_client.post(
        "/api/v1/auth/", 
    data={"username": test_user["email"], 
    "password": test_user["password"]})
    return {
        "access_token": response.cookies.get("access_token"),
        "refresh_token": response.cookies.get("refresh_token")
        }

@pytest.fixture(scope="session")
async def test_project(test_client, auth_cookies):
    project_data = {"project_name": "test_project"}
    await test_client.post(
        "/api/v1/projects/add",
        json=project_data,
        cookies=auth_cookies
    )

@pytest.fixture(scope="session")
async def test_project_id(test_client, auth_cookies, test_project):
    response = await test_client.get(
        "/api/v1/projects/",
        cookies=auth_cookies
    )
    project_list = response.json()
    return next(i["project_public_id"] for i in project_list if i["project_name"] == "test_project")

@pytest.fixture(scope="session")
async def test_task(test_client, test_project_id, auth_cookies):
    task_data = {"task_name":"test_task", "description":"test_task_desc"}
    await test_client.post(
        f"/api/v1/projects/{test_project_id}/tasks/",
        json=task_data,
        cookies=auth_cookies
    )
    
@pytest.fixture(scope="session")
async def test_project_user(test_client, fake_redis):
    user_data = {"email":"test_project@gmail.com", "password":"password123"}
    await test_client.post(
        f"/api/v1/auth/register",
        json=user_data
    )
    redis_data_str = await fake_redis.get("otp:users:test_project@gmail.com")
    redis_data = json.loads(redis_data_str)
    correct_otp = redis_data["otp"]
    code_payload = {"email":"test_project@gmail.com", "otp":correct_otp}
    await test_client.post(
        "/api/v1/auth/verify-otp",
        json=code_payload
    )
    return user_data

@pytest.fixture(scope="session")
async def project_user_id(test_client, test_project_user):
    response = await test_client.post(
        "/api/v1/auth/", 
    data={"username": test_project_user["email"], 
    "password": test_project_user["password"]})
    project_auth_cookies = {
        "access_token": response.cookies.get("access_token"),
        "refresh_token": response.cookies.get("refresh_token")
        }
    get_user_response = await test_client.get(
        "/api/v1/auth/me",
        cookies = project_auth_cookies
    )
    user = get_user_response.json()
    get_user_response.cookies.clear()
    return user['public_id']

@pytest.fixture(scope="session")
async def test_task_id(test_client, test_project_id, test_task, auth_cookies):
    task_response = await test_client.get(
        f"/api/v1/projects/{test_project_id}/tasks/",
        cookies=auth_cookies
    )
    task_list=task_response.json()
    return next(i["task_public_id"] for i in task_list if i["task_name"] == "test_task")
