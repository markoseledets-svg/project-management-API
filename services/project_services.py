from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from repository.projects_repo import ProjectsRepository, UserProjectRepository
from repository.user_repo import UserRepository
from database.db_model import UserProjectRelation, UserRole, ProjectModel, ProjectStatus
from schemas.project_schemas import (
    ProjectWithRoleGetModel, 
    ProjectPostModel, 
    ProjectUpdateModel, 
    PostNewRelation
    )
from typing import Optional
from core.exceptions import NotFoundError, GoneError, UserAlreadyExistsError
from services.permission_check import PermissionService


class ProjectService:
    def __init__(
            self,
            session: AsyncSession,
            ):
        self.session = session
        self.project_repo = ProjectsRepository(session)
        self.user_repo = UserRepository(session)
        self.permission_service = PermissionService(session)
        self.user_project_repo = UserProjectRepository(session)

    async def add_new_project(
            self, 
            project_data:ProjectPostModel, 
            curr_user_id:uuid.UUID
            ) -> None:
        new_project = ProjectModel(
            project_name = project_data.project_name
        )
        self.project_repo.add(new_project)
        await self.session.flush()

        new_relation = UserProjectRelation(
            user_public_id = curr_user_id,
            project_public_id = new_project.project_public_id,
            user_role = UserRole.ADMIN
        )
        self.session.add(new_relation)
        await self.session.commit()
    
    async def get_curr_user_projects(
            self,
            curr_user_id: uuid.UUID
    ) -> Optional[ProjectWithRoleGetModel]:
        return await self.project_repo.get_user_projects_with_roles(curr_user_id)
    
    async def get_project_by_id(self, project_public_id:uuid.UUID) -> Optional[ProjectModel]:
        return await self.project_repo.get_project_by_id_request(project_public_id)
    
    async def update_project(
                                self,
                                curr_user_id:uuid.UUID,
                                project_public_id:uuid.UUID,
                                update_data:ProjectUpdateModel
                                ) -> Optional[ProjectModel|dict]:
        update_model = update_data.model_dump(exclude_unset=True)
        if not update_model:
            return {"message":"No changes provided!"}
        await self.permission_service.verify_user_role(
                                    curr_user_id,
                                    project_public_id,
                                    allowed_roles = (UserRole.EDITOR,UserRole.ADMIN,)
                                    )
        project = await self.get_project_by_id(project_public_id)
        if not project:
            raise NotFoundError()
        if project.status == ProjectStatus.ARCHIVED:
            raise GoneError()
        self.project_repo.update(project,update_model)
        await self.session.commit()
        await self.session.refresh(project)
        return project
    
    async def delete_project(
                            self,
                            project_public_id:uuid.UUID,
                            curr_user_id:uuid.UUID
                            ) -> Optional[ProjectModel]:
        await self.permission_service.verify_user_role(
                                 curr_user_id,
                                 project_public_id,
                                 allowed_roles = (UserRole.ADMIN,)
                                ) 
        project = await self.get_project_by_id(project_public_id)
        if not project:
            raise NotFoundError()
        if project.status == ProjectStatus.ARCHIVED:
            raise GoneError()
        project.status = ProjectStatus.ARCHIVED
        await self.session.commit()
        await self.session.refresh(project)
        return project
    
    async def change_project_status(
                                        self,
                                        curr_user_id:uuid.UUID,
                                        project_public_id:uuid.UUID,
                                        project_status:ProjectStatus
                                        ) -> Optional[ProjectModel]:
            await self.permission_service.verify_user_role(
                                        curr_user_id,
                                        project_public_id,
                                        allowed_roles = (UserRole.ADMIN,)
                                        )
            project = await self.get_project_by_id(project_public_id)
            if not project:
                raise NotFoundError()
            project.status = project_status
            await self.session.commit()
            await self.session.refresh(project)
            return project

    async def add_user_to_project(
                               self, 
                               project_public_id:uuid.UUID,
                               new_relation_data:PostNewRelation, 
                               curr_user_id:uuid.UUID
                               ) -> None:
        await self.permission_service.verify_user_role(
                                 curr_user_id,
                                 project_public_id,
                                 allowed_roles = (UserRole.ADMIN,)
                                )
        new_relation_user_id = await self.user_repo.get_user_id_by_email(new_relation_data.email)
        if not new_relation_user_id:
            raise NotFoundError()
            
        relation_exists = await self.user_project_repo.get_user_role_request(
            new_relation_user_id,
            project_public_id
        )
        if relation_exists:
            raise UserAlreadyExistsError()

        new_relation = UserProjectRelation(
                                            user_public_id=new_relation_user_id,
                                            project_public_id=project_public_id,
                                            user_role=new_relation_data.user_role
        )
        self.session.add(new_relation)
        await self.session.commit()  