from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from repository.tasks_repo import TasksRepository
from database.db_model import TaskModel,UserRole
from schemas.task_schemas import PostTaskModel, UpdateTaskModel,GetTaskModel
from typing import Optional,List
from core.exceptions import NotFoundError
from services.permission_check import PermissionService

class TaskService:
    def __init__(
            self,
            session: AsyncSession,
            ):
        self.session = session
        self.task_repo = TasksRepository(session)
        self.permission_service = PermissionService(session)
    
    async def add_new_task(
                           self,
                           task_data: PostTaskModel, 
                           curr_user_id: uuid.UUID,
                           project_public_id: uuid.UUID
                           ) -> None:
        await self.permission_service.verify_user_role(
                                    curr_user_id,
                                    project_public_id,
                                    allowed_roles=(UserRole.OWNER, UserRole.ADMIN,UserRole.EDITOR,)
                                    )
        new_task = TaskModel(
                            project_public_id = project_public_id,
                            task_name=task_data.task_name, 
                            description=task_data.description
                            )
        self.task_repo.add(new_task)
        await self.session.commit()
    
    async def get_curr_user_project_tasks(
                                    self,
                                    curr_user_id:uuid.UUID,
                                    project_public_id:uuid.UUID
                                    )-> Optional[List[GetTaskModel]]:
        await self.permission_service.verify_user_role(
                                    curr_user_id,
                                    project_public_id,
                                    allowed_roles=(
                                                   UserRole.OWNER, 
                                                   UserRole.ADMIN,
                                                   UserRole.EDITOR,
                                                   UserRole.VIEWER,
                                                   )
                                    )
        return await self.task_repo.get_user_tasks_request(project_public_id)
        
    async def get_task_by_id(
        self, 
        task_public_id:uuid.UUID,
        project_public_id: uuid.UUID
        ) -> Optional[TaskModel]:
        task = await self.task_repo.get_task_by_id_request(task_public_id, project_public_id)
        if not task:
            raise NotFoundError()
        return task
        
    async def update_task(
                          self,
                          update_data:UpdateTaskModel,
                          task_public_id:uuid.UUID, 
                          curr_user_id:uuid.UUID,
                          project_public_id: uuid.UUID
                          ) -> Optional[TaskModel|dict]:
        update_model = update_data.model_dump(exclude_unset=True)
        if not update_model:
            return {"message":"No changes provided!"}
        await self.permission_service.verify_user_role(
                                 curr_user_id,
                                 project_public_id,
                                 allowed_roles = (UserRole.OWNER, UserRole.EDITOR,UserRole.ADMIN,)
                                )
        task_data = await self.get_task_by_id(task_public_id, project_public_id)
        self.task_repo.update(task_data,update_model)
        await self.session.commit()
        await self.session.refresh(task_data)
        return task_data

    async def delete_task(
                          self,
                          task_public_id:uuid.UUID, 
                          user_public_id:uuid.UUID,
                          project_public_id:uuid.UUID
                          ) -> None:
        await self.permission_service.verify_user_role(
                                 user_public_id,
                                 project_public_id,
                                 allowed_roles = (UserRole.OWNER, UserRole.ADMIN,UserRole.EDITOR,)
                                )
        task_data = await self.get_task_by_id(task_public_id, project_public_id)
        await self.session.delete(task_data)
        await self.session.commit()
    
    

    async def change_completed_status(self,
                                      curr_user_id:uuid.UUID,
                                      task_public_id:uuid.UUID,
                                      project_public_id:uuid.UUID
                                      ) -> Optional[TaskModel]:
        await self.permission_service.verify_user_role(
                                 curr_user_id,
                                 project_public_id,
                                 allowed_roles = (UserRole.OWNER, UserRole.EDITOR,UserRole.ADMIN,)
                                )
        task = await self.get_task_by_id(task_public_id, project_public_id)
        task.status = not task.status
        await self.session.commit()
        await self.session.refresh(task)
        return task
