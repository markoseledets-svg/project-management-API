from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import os
from dotenv import load_dotenv

from database.db_config import engine
from schemas.login_schemas import UserGetModel
from services.user_service import AuthServices
from services.task_service import TaskService
from services.project_services import ProjectService
from typing import Annotated, Type, TypeVar, Callable, Any

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth")

async def get_db():
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session

AnotatedSession = Annotated[AsyncSession, Depends(get_db)]
ServiceType = TypeVar("ServiceType")

def get_service(service_class: Type[Any]) -> Callable:
    def factory(db: AnotatedSession) -> Any: 
        return service_class(db)
    return factory

AuthServiceDep = Annotated[AuthServices, Depends(get_service(AuthServices))]
TaskServiceDep = Annotated[TaskService, Depends(get_service(TaskService))]
ProjectServiceDep = Annotated[ProjectService, Depends(get_service(ProjectService))]

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    ) -> UserGetModel:
    auth_service = AuthServices(db)
    return await auth_service.get_user_credentials(token)
    