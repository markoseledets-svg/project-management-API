from sqlalchemy.sql.elements import UnaryExpression
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from typing import List,Optional
from repository.base_repo import BaseRepository
from database.db_model import TaskModel, UserModel
from schemas.task_schemas import GetTaskModel, TaskWithAssigneeModel
from schemas.sort_schemas import SortOrder, TaskSortField

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
    
    def _get_sort_params(
        self,
        sort_by: TaskSortField,
        sort_order: SortOrder
    ) -> UnaryExpression:
        SORT_MAP = {
            TaskSortField.CREATED_AT: TaskModel.task_public_id,
            TaskSortField.TASK_NAME: TaskModel.task_name
        }
        column = SORT_MAP.get(sort_by, TaskModel.task_public_id)
        order_expr = column.desc() if sort_order == SortOrder.DESC else column.asc()
        return order_expr
    async def get_user_tasks_request(
        self,
        project_public_id: uuid.UUID,
        page: int,
        limit: int,
        sort_by: TaskSortField,
        sort_order: SortOrder
        ) -> Optional[List[TaskWithAssigneeModel]]:
        order_by = self._get_sort_params(sort_by, sort_order)
        tasks = await self.session.execute(
            select(TaskModel, UserModel.email)
            .outerjoin(UserModel, TaskModel.assignee_id == UserModel.public_id)
            .where(TaskModel.project_public_id == project_public_id)
            .order_by(order_by, TaskModel.task_public_id)
            .limit(limit)
            .offset((page-1)*limit)
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

    async def count_tasks(self, project_public_id: uuid.UUID) -> int:
        return await self.get_row_count_by(project_public_id=project_public_id)