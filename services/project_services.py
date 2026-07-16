from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from repository.projects_repo import ProjectsRepository, UserProjectRepository
from repository.user_repo import UserRepository
from database.db_model import UserProjectRelation, UserRole, ProjectModel, ProjectStatus
from schemas.project_schemas import (
    ProjectWithRoleGetModel, 
    ProjectPostModel, 
    ProjectUpdateModel, 
    PostNewRelation,
    GetUserDataWithRole,
    UpdateUserRole,
    )
from typing import Optional, List
from core.exceptions import NotFoundError, GoneError, ConflictError, ForbiddenError, DataValidationError
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
            user_role = UserRole.OWNER
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
                                    allowed_roles = (UserRole.EDITOR,UserRole.ADMIN, UserRole.OWNER,)
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
    
    async def soft_delete_project(
                            self,
                            project_public_id:uuid.UUID,
                            curr_user_id:uuid.UUID
                            ) -> Optional[ProjectModel]:
        await self.permission_service.verify_user_role(
                                 curr_user_id,
                                 project_public_id,
                                 allowed_roles = (UserRole.ADMIN, UserRole.OWNER,)
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
                                        allowed_roles = (UserRole.ADMIN, UserRole.OWNER,)
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
        
        user_role = await self.permission_service.verify_user_role(
            curr_user_id,
            project_public_id,
            allowed_roles=(UserRole.ADMIN, UserRole.OWNER,)
        )
        new_relation_user_id = await self.user_repo.get_user_id_by_email(new_relation_data.email)
        if not new_relation_user_id:
            raise NotFoundError()
        relation_exists = await self.user_project_repo.get_user_role_request(
            new_relation_user_id,
            project_public_id
        )
        if relation_exists:
            raise ConflictError(detail="User with this email already in project members!")
        self.permission_service.verify_user_hierarchy(
            user_role,
            new_user_role=new_relation_data.user_role
        )
        new_relation = UserProjectRelation(
                                            user_public_id=new_relation_user_id,
                                            project_public_id=project_public_id,
                                            user_role=new_relation_data.user_role
        )
        self.session.add(new_relation)
        await self.session.commit()  

    async def get_members_list(
                                self,
                                user_public_id: uuid.UUID,
                                project_public_id: uuid.UUID
                                ) -> Optional[List[GetUserDataWithRole]]:
        await self.permission_service.verify_user_role(
            user_public_id,
            project_public_id,
            allowed_roles=(UserRole.OWNER, UserRole.ADMIN)
        )
        return await self.user_project_repo.get_user_data_with_roles(project_public_id)

    async def delete_user_from_project(
                                        self,
                                        user_public_id:uuid.UUID,
                                        target_user_public_id:uuid.UUID,
                                        project_public_id:uuid.UUID
                                        ) -> None:
        user_role = await self.permission_service.verify_user_role(
            user_public_id,
            project_public_id,
            allowed_roles=(UserRole.OWNER, UserRole.ADMIN)
        )
        relation_data = await self.user_project_repo.get_relation_data(
            target_user_public_id,
            project_public_id
        )
        if not relation_data:
            raise NotFoundError()
        if user_public_id == target_user_public_id:
            raise ConflictError(detail="You can't delete yourself!")
        self.permission_service.verify_user_hierarchy(user_role, relation_data.user_role)
        await self.user_project_repo.delete(relation_data)
        await self.session.commit()

    async def change_user_role(
                                self,
                                user_public_id: uuid.UUID,
                                new_role_data: UpdateUserRole,
                                project_public_id: uuid.UUID
                                ) -> None:
        user_role = await self.permission_service.verify_user_role(
            user_public_id,
            project_public_id,
            allowed_roles=(UserRole.ADMIN, UserRole.OWNER)
        )
        relation_data = await self.user_project_repo.get_relation_data(new_role_data.user_public_id, project_public_id)
        if not relation_data:
            raise NotFoundError()
        if user_public_id  == relation_data.user_public_id:
            raise ConflictError(detail="You cant change your own role!")
        self.permission_service.verify_user_hierarchy(
            user_role,
            relation_data.user_role,
            new_role_data.user_role
        )
        relation_data.user_role = new_role_data.user_role
        await self.session.commit()
        
    async def leave_from_project(
                                 self,
                                 user_public_id: uuid.UUID,
                                 project_public_id: uuid.UUID  
                                 ) -> None:
        relation_data = await self.user_project_repo.get_relation_data(user_public_id, project_public_id)
        if not relation_data:
            raise NotFoundError()
        elif relation_data.user_role == UserRole.OWNER:
            members_count = await self.user_project_repo.count_project_users(project_public_id)
            if members_count > 1:
                raise ConflictError(detail="Owners cant leave from project! Assign owner another project member on dashboard!")
            project = await self.project_repo.get_project_by_id_request(project_public_id)
            if not project:
                raise NotFoundError()
            await self.project_repo.delete(project)
            await self.session.commit() 
            return
        await self.session.delete(relation_data)
        await self.session.commit() 

    async def assign_new_owner(
        self,
        user_public_id: uuid.UUID,
        project_public_id: uuid.UUID,
        target_user_id: uuid.UUID
        ) -> None:
        if user_public_id == target_user_id:
            raise ConflictError(detail="You can`t assign owner!")
        curr_user_relation_data = await self.user_project_repo.get_relation_data(
            user_public_id,
            project_public_id
        )
        target_user_relation_data = await self.user_project_repo.get_relation_data(
            target_user_id,
            project_public_id
        )
 
        if not curr_user_relation_data or not target_user_relation_data:
            raise NotFoundError()
        if curr_user_relation_data.user_role != UserRole.OWNER:
            raise ForbiddenError()
        curr_user_relation_data.user_role = UserRole.ADMIN
        await self.session.flush()
        target_user_relation_data.user_role = UserRole.OWNER
        await self.session.commit()
    
    async def verify_and_delete_project(
                                        self,
                                        user_public_id: uuid.UUID,
                                        project_public_id: uuid.UUID,
                                        project_name: str
                                        ) -> None:
        await self.permission_service.verify_user_role(
            user_public_id,
            project_public_id,
            allowed_roles=(UserRole.OWNER,)
        )
        project = await self.project_repo.get_project_by_id_request(project_public_id)
        if not project:
            raise NotFoundError()
        if project.project_name != project_name:
            raise DataValidationError()
        if project.status != ProjectStatus.ARCHIVED:
            raise ConflictError(detail="Project should be archived before deletion!")
        await self.project_repo.delete(project)
        await self.session.commit()
        
