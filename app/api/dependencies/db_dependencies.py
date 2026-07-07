from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Cookie

from database.db_config import engine
from schemas.login_schemas import UserGetModel
from services.user_service import AuthServices
from services.task_service import TaskService
from services.project_services import ProjectService
from typing import Annotated, Type, TypeVar, Callable, Any
from app.api.dependencies.redis_dependencies import RedisClient
from core.exceptions import AuthFailedError

async def get_db():
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session

AnotatedSession = Annotated[AsyncSession, Depends(get_db)]
ServiceType = TypeVar("ServiceType")

def get_service(service_class: Type[Any]) -> Callable:
    def factory(db: AnotatedSession) -> Any: 
        return service_class(db)
    return factory

TaskServiceDep = Annotated[TaskService, Depends(get_service(TaskService))]
ProjectServiceDep = Annotated[ProjectService, Depends(get_service(ProjectService))]

def get_auth_service(db:AnotatedSession, redis:RedisClient):
    return AuthServices(db, redis)


AuthServiceDep = Annotated[AuthServices, Depends(get_auth_service)]

async def get_current_user(
    auth_services: AuthServiceDep,
    access_token: str | None = Cookie(default=None),
    ) -> UserGetModel:
    if not access_token:
        raise AuthFailedError()
    return await auth_services.get_user_credentials(access_token)
    