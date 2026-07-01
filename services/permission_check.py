import uuid
from sqlalchemy.ext.asyncio import AsyncSession

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
                                ) -> None:
        user_role = await self.user_project_repo.get_user_role_request(curr_user_id,project_public_id)
        if not user_role:
            raise NotFoundError()
        if user_role not in allowed_roles:
            raise ForbiddenError()