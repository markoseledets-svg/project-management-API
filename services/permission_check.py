import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from core.exceptions import NotFoundError, ForbiddenError
from database.db_model import UserRole
from repository.projects_repo import UserProjectRepository

class PermissionService:
    def __init__(
                self, 
                session: AsyncSession
                ):
          self.session = session
          self.user_project_repo = UserProjectRepository(session)
          
    async def verify_user_role(
                                self,
                                curr_user_id:uuid.UUID,
                                project_public_id:uuid.UUID,
                                allowed_roles:tuple[UserRole, ...]
                                ) -> Optional[UserRole]:
        user_role = await self.user_project_repo.get_user_role_request(curr_user_id,project_public_id)
        if not user_role:
            raise NotFoundError()
        if user_role not in allowed_roles:
            raise ForbiddenError()
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
          