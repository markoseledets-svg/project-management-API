from sqlalchemy.sql.elements import UnaryExpression
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from typing import List,Optional
from repository.base_repo import BaseRepository
from database.db_model import TaskModel, UserModel
from schemas.task_schemas import GetTaskModel, TaskWithAssigneeModel
from schemas.sort_schemas import SortOrder, TaskSortField
from schemas.filter_schemas import TaskFilters
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
    def _build_predicates(
        self,
        project_public_id: uuid.UUID,
        filters: TaskFilters
    ) -> list:
        predicates = [
            TaskModel.project_public_id == project_public_id
        ]
        if filters.status is not None:
            predicates.append(TaskModel.status == filters.status)
        if filters.has_assignee is not None:
            if filters.has_assignee:
                predicates.append(TaskModel.assignee_id.is_not(None))
            else:
                predicates.append(TaskModel.assignee_id.is_(None))
        if filters.search:
            pattern = f'%{filters.search}%'
            predicates.append(
                or_(
                    TaskModel.task_name.ilike(pattern),
                    UserModel.email.ilike(pattern)
                )
            )
        return predicates
        
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
        sort_order: SortOrder,
        filters: TaskFilters
        ) -> Optional[List[TaskWithAssigneeModel]]:
        order_by = self._get_sort_params(sort_by, sort_order)
        predicates = self._build_predicates(project_public_id, filters)
        tasks = await self.session.execute(
            select(TaskModel, UserModel.email)
            .outerjoin(UserModel, TaskModel.assignee_id == UserModel.public_id)
            .where(*predicates)
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

    async def count_tasks(self, project_public_id: uuid.UUID, filters: TaskFilters) -> int:
        predicates = self._build_predicates(project_public_id, filters)
        stmt = (
            select(func.count())
            .select_from(TaskModel)
            .outerjoin(UserModel, UserModel.public_id == TaskModel.assignee_id)
            .where(*predicates)
            )
        return (await self.session.scalar(stmt)) or 0
        