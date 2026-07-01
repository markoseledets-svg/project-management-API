from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from typing import List,Optional
from repository.base_repo import BaseRepository
from database.db_model import UserProjectRelation, ProjectModel
from schemas.project_schemas import ProjectWithRoleGetModel

class ProjectsRepository(BaseRepository[ProjectModel]):
    def __init__(self, session:AsyncSession):
        super().__init__(ProjectModel, session)
    
    async def get_project_by_id_request(self,project_public_id:uuid.UUID) -> Optional[ProjectModel]:
        return await self.get_by(project_public_id = project_public_id)

    async def get_user_projects_with_roles(self,user_public_id:uuid.UUID) -> Optional[List[ProjectWithRoleGetModel]]:
        projects_with_roles_obj = await self.session.execute(
            select(ProjectModel, UserProjectRelation.user_role)
            .join(UserProjectRelation, ProjectModel.project_public_id == UserProjectRelation.project_public_id)
            .where(UserProjectRelation.user_public_id == user_public_id)
        )
        project_list = []
        for project,role in projects_with_roles_obj.all():
            project_with_role = ProjectWithRoleGetModel(
                project_public_id = project.project_public_id,
                project_name = project.project_name,
                status = project.status,
                created_at = project.created_at,
                updated_at = project.updated_at,
                user_role = role
            )
            project_list.append(project_with_role)
        return project_list

class UserProjectRepository(BaseRepository[UserProjectRelation]):
    def __init__(self, session:AsyncSession):
        super().__init__(UserProjectRelation, session)
    
    async def get_user_role_request(self,user_public_id:uuid.UUID,project_public_id:uuid.UUID):
        obj_role = await self.session.execute(select(UserProjectRelation.user_role)
                                        .where(
                                               UserProjectRelation.user_public_id == user_public_id, 
                                               UserProjectRelation.project_public_id == project_public_id
                                               )
                                        )
        return obj_role.scalar_one_or_none()