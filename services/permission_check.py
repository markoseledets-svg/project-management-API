import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from core.exceptions import NotFoundError, ForbiddenError, ConflictError
from database.db_model import UserRole, ProjectStatus
from repository.projects_repo import UserProjectRepository, ProjectsRepository

class PermissionService:
    def __init__(
                self, 
                session: AsyncSession
                ):
          self.session = session
          self.user_project_repo = UserProjectRepository(session)
          self.project_repo = ProjectsRepository(session)
          
    async def verify_user_role(
                                self,
                                curr_user_id:uuid.UUID,
                                project_public_id:uuid.UUID,
                                allowed_roles:tuple[UserRole, ...],
                                check_active: bool = True
                                ) -> Optional[UserRole]:
        user_role = await self.user_project_repo.get_user_role_request(curr_user_id,project_public_id)
        if not user_role:
            raise NotFoundError()
        if user_role not in allowed_roles:
            raise ForbiddenError()
        if check_active:    
            project_status = await self.project_repo.get_status_by_id(project_public_id)
            if not project_status or project_status == ProjectStatus.ARCHIVED:
                raise ConflictError(detail='Project is archived!')
        return user_role
    
    def verify_user_hierarchy(
        self,
        curr_user_role: UserRole,
        relation_user_role: UserRole | None = None,
        new_user_role: UserRole | None = None
        ) -> None:
        if curr_user_role == relation_user_role:
            raise ForbiddenError()
        if curr_user_role == UserRole.OWNER and new_user_role !=UserRole.OWNER:
            return
        if relation_user_role in (UserRole.ADMIN, UserRole.OWNER):
            raise ForbiddenError()
        if new_user_role in (UserRole.ADMIN, UserRole.OWNER):
            raise ForbiddenError()
          