from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from repository.tasks_repo import TasksRepository
from repository.projects_repo import UserProjectRepository
from database.db_model import TaskModel,UserRole, TaskStatus
from schemas.task_schemas import PostTaskModel, UpdateTaskModel,GetTaskModel
from typing import Optional,List
from core.exceptions import NotFoundError, ForbiddenError, ConflictError
from services.permission_check import PermissionService

class TaskService:
    def __init__(
            self,
            session: AsyncSession,
            ):
        self.session = session
        self.task_repo = TasksRepository(session)
        self.permission_service = PermissionService(session)
        self.user_project_repo = UserProjectRepository(session)
    
    async def add_new_task(
                           self,
                           task_data: PostTaskModel, 
                           curr_user_id: uuid.UUID,
                           project_public_id: uuid.UUID
                           ) -> None:
        allowed_roles=(UserRole.OWNER, UserRole.ADMIN,UserRole.EDITOR,)
        await self.permission_service.verify_user_role(
                                    curr_user_id,
                                    project_public_id,
                                    allowed_roles
                                    )
        if task_data.assignee_id:
            user_role = await self.user_project_repo.get_user_role_request(
                task_data.assignee_id,
                project_public_id
            )
            if not user_role or user_role not in allowed_roles:
                raise ForbiddenError(detail="User dont have enough permission to process tasks in this project!")
        self.task_repo.create(
                            project_public_id = project_public_id,
                            task_name=task_data.task_name, 
                            description=task_data.description,
                            assignee_id = task_data.assignee_id if task_data.assignee_id else None,
                            status = TaskStatus.IN_PROGRESS if task_data.assignee_id else TaskStatus.TODO
                            )
        
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
                                                   ),
                                    check_active=False
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
                          ) -> TaskModel:
        update_model = update_data.model_dump(exclude_unset=True)
        await self.permission_service.verify_user_role(
                                 curr_user_id,
                                 project_public_id,
                                 allowed_roles = (UserRole.OWNER, UserRole.EDITOR,UserRole.ADMIN,)
                                )
        task_data = await self.get_task_by_id(task_public_id, project_public_id)
        self.task_repo.update(task_data,update_model)
        await self.session.commit()
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
    
    def _validate_task_access(
                            self, 
                            task:TaskModel, 
                            user_role:UserRole, 
                            user_public_id: uuid.UUID,
                            allowed_status: TaskStatus
                            ) -> None:
        if user_role == UserRole.EDITOR and task.assignee_id != user_public_id:
            raise ForbiddenError(detail="Editors can only modify their own tasks!")
        if task.status != allowed_status:
            raise ForbiddenError(detail="You can't change task status from current!")
        if not task.assignee_id:
            raise ForbiddenError(detail="Cannot change task statuses without assignee!")
    
    async def change_task_status(self, task:TaskModel, new_status:TaskStatus) -> TaskModel:
        task.status = new_status
        await self.session.commit()
        return task

    async def editor_task_status_change(
                            self,
                            user_public_id: uuid.UUID,
                            task_public_id: uuid.UUID,
                            project_public_id: uuid.UUID,
                            new_status: TaskStatus,
                            ) -> Optional[TaskModel]:
        user_role = await self.permission_service.verify_user_role(
            user_public_id,
            project_public_id,
            allowed_roles=(UserRole.OWNER, UserRole.ADMIN, UserRole.EDITOR,)
        )
        task = await self.get_task_by_id(task_public_id, project_public_id)
        self._validate_task_access(
            task,
            user_role,
            user_public_id,
            TaskStatus.IN_PROGRESS if new_status == TaskStatus.REVIEW else TaskStatus.REVIEW
        )
        return await self.change_task_status(task, new_status)
    
    async def admin_task_status_change(
                                self,
                                user_public_id: uuid.UUID,
                                task_public_id: uuid.UUID,
                                project_public_id: uuid.UUID,
                                new_status: TaskStatus,
                                allowed_prev_status: TaskStatus
                                ) -> TaskModel:
        await self.permission_service.verify_user_role(
            user_public_id,
            project_public_id,
            allowed_roles=(UserRole.OWNER, UserRole.ADMIN,)
        )
        task = await self.get_task_by_id(task_public_id, project_public_id)
        if task.status != allowed_prev_status:
            raise ForbiddenError(detail="Cannot change task status from current!")
        return await self.change_task_status(task, new_status)
    
    async def send_task_to_review(
                                    self,
                                    user_public_id: uuid.UUID,
                                    task_public_id: uuid.UUID,
                                    project_public_id: uuid.UUID
                                    ) -> TaskModel:
        return await self.editor_task_status_change(
            user_public_id,
            task_public_id,
            project_public_id,
            TaskStatus.REVIEW
        )
    
    async def cancel_task_review_status(
                                    self,
                                    user_public_id: uuid.UUID,
                                    task_public_id: uuid.UUID,
                                    project_public_id: uuid.UUID
                                    ) -> TaskModel:
        return await self.editor_task_status_change(
            user_public_id,
            task_public_id,
            project_public_id,
            TaskStatus.IN_PROGRESS
        )
    
    async def change_status_to_completed(
                                        self,
                                        user_public_id: uuid.UUID,
                                        task_public_id: uuid.UUID,
                                        project_public_id: uuid.UUID
                                        ) -> TaskModel:
        return await self.admin_task_status_change(
            user_public_id,
            task_public_id,
            project_public_id,
            TaskStatus.COMPLETED,
            TaskStatus.REVIEW
        )
    
    async def cancel_completed_status(
                                        self,
                                        user_public_id: uuid.UUID,
                                        task_public_id: uuid.UUID,
                                        project_public_id: uuid.UUID
                                        ) -> TaskModel:
        return await self.admin_task_status_change(
            user_public_id,
            task_public_id,
            project_public_id,
            TaskStatus.REVIEW,
            TaskStatus.COMPLETED
        )
    
    async def user_self_assign_to_task(
                                        self,
                                        user_public_id: uuid.UUID,
                                        task_public_id: uuid.UUID,
                                        project_public_id: uuid.UUID
                                        ) -> TaskModel:
        await self.permission_service.verify_user_role(
            user_public_id,
            project_public_id,
            allowed_roles=(UserRole.OWNER, UserRole.ADMIN, UserRole.EDITOR,)
        )
        task = await self.get_task_by_id(
            task_public_id,
            project_public_id
        )
        if task.status != TaskStatus.TODO or task.assignee_id is not None:
            raise ForbiddenError(detail="Task is already assigned to someone else!")
        task.assignee_id = user_public_id
        task.status = TaskStatus.IN_PROGRESS
        await self.session.commit()
        return task
    
    async def assign_user_to_task(
                                    self,
                                    user_public_id: uuid.UUID,
                                    task_public_id: uuid.UUID,
                                    project_public_id: uuid.UUID,
                                    target_user_public_id: uuid.UUID
                                    ) -> TaskModel:
        await self.permission_service.verify_user_role(
            user_public_id,
            project_public_id,
            allowed_roles = (UserRole.OWNER, UserRole.ADMIN,)
        )
        task = await self.get_task_by_id(task_public_id, project_public_id)
        if task.status in (TaskStatus.REVIEW, TaskStatus.COMPLETED):
            raise ForbiddenError(detail="Cannot modify assignee while task is in review or completed!")
        target_user_role = await self.user_project_repo.get_user_role_request(
            target_user_public_id,
            project_public_id
        )
        if target_user_role is None or target_user_role == UserRole.VIEWER:
            raise ForbiddenError(detail="User don't have enough permissions to be assigned!")
        task.assignee_id = target_user_public_id
        task.status = TaskStatus.IN_PROGRESS
        await self.session.commit()
        return task
    
    async def delete_task_assignee(
                                    self,
                                    user_public_id: uuid.UUID,
                                    project_public_id: uuid.UUID,
                                    task_public_id: uuid.UUID
                                    ) -> TaskModel:
        await self.permission_service.verify_user_role(
            user_public_id,
            project_public_id,
            allowed_roles=(UserRole.OWNER, UserRole.ADMIN,)
        )
        task = await self.get_task_by_id(task_public_id, project_public_id)
        if task.status in (TaskStatus.REVIEW, TaskStatus.COMPLETED):
            raise ForbiddenError(detail="Cannot modify assignee while task is in review or completed!")
        if not task.assignee_id:
            raise ConflictError()
        task.assignee_id = None
        task.status = TaskStatus.TODO
        await self.session.commit()
        return task
