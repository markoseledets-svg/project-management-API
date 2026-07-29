import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import pytest
from httpx import AsyncClient, ASGITransport
from fakeredis import FakeAsyncRedis
from unittest.mock import patch

from core.security import generate_access_jwt, generate_refresh_jwt
from tests.factories.base import BaseFactory
from tests.factories.users import UserFactory, RefreshFactory
from tests.factories.invitations import InvitationFactory
from tests.factories.projects import ProjectFactory, UserProjectFactory
from tests.factories.tasks import TaskFactory
from database.db_model import Base, UserRole, InvitationStatus, ProjectStatus
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

@pytest.fixture(scope='session')
async def test_engine():
    engine = create_async_engine(DB_URL, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(autouse=True)
async def db_session(test_engine):
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        BaseFactory.__async_session__ = session
        yield session
        BaseFactory.__async_session__ = None
        await session.rollback()

@pytest.fixture
async def test_client(test_engine, fake_redis, db_session):
  
    async def get_fake_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = get_fake_redis
    async def get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = get_test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture
async def test_user():
    return await UserFactory.create_async()

@pytest.fixture
async def test_access_token(test_user):
    return generate_access_jwt(test_user.public_id)

@pytest.fixture
async def test_refresh_token(test_user):
    refresh_record = await RefreshFactory.create_async(user_public_id = test_user.public_id)
    return generate_refresh_jwt(test_user.public_id, refresh_record.token_public_id)

@pytest.fixture
async def auth_cookies(test_access_token, test_refresh_token):
    return {
        "access_token": test_access_token,
        "refresh_token": test_refresh_token
    }

@pytest.fixture
async def test_project(test_user):
    project = await ProjectFactory.create_async(status = ProjectStatus.ACTIVE)
    await UserProjectFactory.create_async(
        user_public_id = test_user.public_id,
        project_public_id = project.project_public_id,
        user_role = UserRole.OWNER,
    )
    return project



@pytest.fixture
async def test_task(test_project):
    return await TaskFactory.create_async(project_public_id = test_project.project_public_id)

@pytest.fixture
async def test_project_user(test_user):
    return await UserFactory.create_async()

@pytest.fixture
async def project_user_cookies(test_project_user):
    access_token = generate_access_jwt(test_project_user.public_id)
    refresh_record = await RefreshFactory.create_async(user_public_id = test_project_user.public_id)
    refresh_token = generate_refresh_jwt(
        test_project_user.public_id,
        refresh_record.token_public_id
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }

@pytest.fixture
async def test_project_member(test_project, test_project_user):
    return await UserProjectFactory.create_async(
        user_public_id = test_project_user.public_id,
        project_public_id = test_project.project_public_id,
        user_role = UserRole.ADMIN
    )
@pytest.fixture
async def test_invitation(test_user, test_project_user, test_project):
    return await InvitationFactory.create_async(
        project_public_id = test_project.project_public_id,
        sender_public_id = test_user.public_id,
        target_user_public_id = test_project_user.public_id,
        user_role = UserRole.ADMIN,
        status = InvitationStatus.PENDING
    )