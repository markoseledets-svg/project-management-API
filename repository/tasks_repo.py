from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from typing import List,Optional
from repository.base_repo import BaseRepository
from database.db_model import TaskModel, UserModel
from schemas.task_schemas import GetTaskModel, TaskWithAssigneeModel


class TasksRepository(BaseRepository[TaskModel]):
    def __init__(self, session:AsyncSession):
        super().__init__(TaskModel, session)
    
    async def get_task_by_id_request(
                                    self, 
                                    task_public_id:uuid.UUID,
                                    project_public_id: uuid.UUID
                                    ) -> Optional[GetTaskModel]:
        return await self.get_by(
            task_public_id = task_public_id,
            project_public_id = project_public_id
        )
    
    
    async def get_user_tasks_request(self,project_public_id:uuid.UUID) -> Optional[List[TaskWithAssigneeModel]]:
        tasks = await self.session.execute(
            select(TaskModel, UserModel.email)
            .outerjoin(UserModel, TaskModel.assignee_id == UserModel.public_id)
            .where(TaskModel.project_public_id == project_public_id)
        )
        task_list = []
        for task, email in tasks.all():
            task_i = TaskWithAssigneeModel(
                task_name=task.task_name,
                description=task.description,
                task_public_id=task.task_public_id,
                assignee_id=task.assignee_id,
                status=task.status,
                email=email
            )
            task_list.append(task_i)
        return task_list

