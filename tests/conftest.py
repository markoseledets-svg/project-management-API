import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import pytest
from httpx import AsyncClient, ASGITransport
from fakeredis import FakeAsyncRedis
from unittest.mock import patch, AsyncMock, MagicMock

from core.security import generate_access_jwt, generate_refresh_jwt, hash_data, generate_restore_jwt
from tests.factories.base import BaseFactory
from tests.factories.users import UserFactory, RefreshFactory, AuthIdentityFactory, RAW_PASSWORD
from tests.factories.invitations import InvitationFactory
from tests.factories.projects import ProjectFactory, UserProjectFactory
from tests.factories.tasks import TaskFactory
from database.db_model import Base, UserRole, InvitationStatus, ProjectStatus, TaskStatus, RegistrationIdentity
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

@pytest.fixture(autouse=True)
async def clear_redis_between_tests(fake_redis):
    yield
    await fake_redis.flushall()

@pytest.fixture
async def test_client(test_engine, fake_redis, db_session):
    app.state.redis = fake_redis
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
async def test_refresh_record(test_user):
    return await RefreshFactory.create_async(user_public_id = test_user.public_id)

@pytest.fixture
async def test_access_token(test_user, test_refresh_record):
    return generate_access_jwt(test_user.public_id, test_refresh_record.family_id)

@pytest.fixture
async def test_refresh_token(test_user, test_refresh_record):
    return generate_refresh_jwt(test_user.public_id, test_refresh_record.token_public_id)

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
    return await TaskFactory.create_async(
        project_public_id = test_project.project_public_id,
        assignee_id = None,
        status = TaskStatus.TODO
    )

@pytest.fixture
async def test_unassigned_task(test_project):
    return await TaskFactory.create_async(
        project_public_id = test_project.project_public_id,
        assignee_id = None,
        status = TaskStatus.TODO
    )

@pytest.fixture
async def test_project_user(test_user):
    return await UserFactory.create_async()

@pytest.fixture
async def project_user_cookies(test_project_user):
    refresh_record = await RefreshFactory.create_async(user_public_id = test_project_user.public_id)
    access_token = generate_access_jwt(test_project_user.public_id, refresh_record.family_id)
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

@pytest.fixture
async def test_task_assignee(test_task, test_project, test_project_user):
    return await TaskFactory.create_async(
        project_public_id = test_project.project_public_id,
        assignee_id = test_project_user.public_id,
        status = TaskStatus.IN_PROGRESS
    )

@pytest.fixture
async def test_task_review(test_project, test_project_user):
    return await TaskFactory.create_async(
        project_public_id = test_project.project_public_id,
        assignee_id = test_project_user.public_id,
        status = TaskStatus.REVIEW
    )

@pytest.fixture
async def test_task_completed(test_project, test_project_user):
    return await TaskFactory.create_async(
        project_public_id = test_project.project_public_id,
        assignee_id = test_project_user.public_id,
        status = TaskStatus.COMPLETED
    )

@pytest.fixture
async def test_local_identity(test_user):
    hashed_password = hash_data(RAW_PASSWORD)
    return await AuthIdentityFactory.create_async(
        user_public_id = test_user.public_id,
        hashed_password=hashed_password,
        provider=RegistrationIdentity.LOCAL
    )

@pytest.fixture
async def test_google_identity(test_user):
    return await AuthIdentityFactory.create_async(
        user_public_id=test_user.public_id,
        provider=RegistrationIdentity.GOOGLE,
    )

@pytest.fixture
def mock_google_oauth():
    with patch("app.api.v1.routers.auth_routes.oauth.google.authorize_access_token", new_callable=AsyncMock) as mock:
        def configure(email="google_user@test.com", sub="google-sub-12345"):
            mock.return_value = {
                "userinfo": {
                    "email": email,
                    "sub": sub
                }
            }
        configure()
        mock.configure = configure
        yield mock

@pytest.fixture
def mock_github_oauth():
    with patch("app.api.v1.routers.auth_routes.oauth.github.authorize_access_token", new_callable=AsyncMock) as mock_auth, \
         patch("app.api.v1.routers.auth_routes.oauth.github.get", new_callable=AsyncMock) as mock_get:
        
        mock_auth.return_value = {"access_token": "mock_gh_token"}

        def configure(user_id=12345678, email="github_user@test.com", verified=True, primary=True):
            user_resp = MagicMock()
            user_resp.json.return_value = {"id": user_id}
            
            emails_resp = MagicMock()
            emails_resp.json.return_value = [
                {"email": email, "primary": primary, "verified": verified}
            ]

            async def mock_fetch(url, token=None):
                return user_resp if url == "user" else emails_resp

            mock_get.side_effect = mock_fetch

        configure()
        mock_auth.configure = configure
        yield mock_auth, mock_get