from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import UnaryExpression
from uuid import UUID 

from typing import List,Optional
from repository.base_repo import BaseRepository
from database.db_model import UserProjectRelation, ProjectModel, UserModel
from schemas.project_schemas import ProjectWithRoleGetModel, GetUserDataWithRole
from schemas.sort_schemas import ProjectSortField, SortOrder
from schemas.filter_schemas import ProjectFilters

class ProjectsRepository(BaseRepository[ProjectModel]):
    def __init__(self, session:AsyncSession):
        super().__init__(ProjectModel, session)
    
    async def get_project_by_id_request(self,project_public_id: UUID) -> Optional[ProjectModel]:
        return await self.get_by(project_public_id = project_public_id)
    
    def _build_predicates(
        self, 
        user_public_id: UUID, 
        filters: ProjectFilters
        ) -> list:
        predicates = [
            UserProjectRelation.user_public_id == user_public_id
        ]
        if filters.status is not None:
            predicates.append(ProjectModel.status == filters.status) 
        if filters.search:
            pattern = f'%{filters.search}%'
            predicates.append(ProjectModel.project_name.ilike(pattern))
        return predicates

    def _get_sort_params(
        self, 
        sort_by: ProjectSortField, 
        sort_order: SortOrder
        ) -> UnaryExpression:
        SORT_MAP = {
            ProjectSortField.CREATED_AT: ProjectModel.created_at,
            ProjectSortField.UPDATED_AT: ProjectModel.updated_at,
            ProjectSortField.PROJECT_NAME: ProjectModel.project_name,
        }
        column = SORT_MAP.get(sort_by, ProjectModel.updated_at)
        order_expr = column.desc() if sort_order == SortOrder.DESC else column.asc()
        return order_expr

    async def get_user_projects_with_roles(
        self,
        user_public_id: UUID,
        limit: int,
        page: int,
        sort_by: ProjectSortField,
        sort_order: SortOrder,
        filters: ProjectFilters
        ) -> Optional[List[ProjectWithRoleGetModel]]:
        order_by = self._get_sort_params(sort_by, sort_order)
        predicates = self._build_predicates(user_public_id, filters)
        projects_with_roles_obj = await self.session.execute(
            select(ProjectModel, UserProjectRelation.user_role)
            .join(UserProjectRelation, ProjectModel.project_public_id == UserProjectRelation.project_public_id)
            .where(*predicates)
            .order_by(order_by, ProjectModel.project_public_id.desc())
            .limit(limit)
            .offset((page-1)*limit)
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
    
    async def get_status_by_id(self, project_public_id:  UUID):
        return await self.get_columns_by('status', project_public_id=project_public_id)

    async def count_users_projects(self, user_public_id: UUID, filters: ProjectFilters) -> int:
        predicates = self._build_predicates(user_public_id, filters)
        stmt = (
            select(func.count())
            .select_from(ProjectModel)
            .join(UserProjectRelation, UserProjectRelation.project_public_id == ProjectModel.project_public_id)
            .where(*predicates)
        )
        return (await self.session.scalar(stmt)) or 0

class UserProjectRepository(BaseRepository[UserProjectRelation]):
    def __init__(self, session:AsyncSession):
        super().__init__(UserProjectRelation, session)
    
    async def get_user_role_request(self,user_public_id: UUID,project_public_id: UUID):
        obj_role = await self.session.execute(select(UserProjectRelation.user_role)
                                        .where(
                                               UserProjectRelation.user_public_id == user_public_id, 
                                               UserProjectRelation.project_public_id == project_public_id
                                               )
                                        )
        return obj_role.scalar_one_or_none()
    
    async def get_user_data_with_roles(
                                    self, 
                                    project_public_id:  UUID,
                                    page: int,
                                    limit: int
                                    ) -> Optional[List[GetUserDataWithRole]]:
        project_users_obj = await self.session.execute(
            select(UserModel.public_id, UserModel.email, UserProjectRelation.user_role).join(
            UserProjectRelation, 
            and_(UserModel.public_id == UserProjectRelation.user_public_id,
            UserProjectRelation.project_public_id == project_public_id))
            .limit(limit)
            .offset((page - 1) * limit)
            )
        user_data_with_roles = []
        for public_id, email, role in project_users_obj.all():
            user_data_with_roles.append({"public_id":public_id,"email":email, "user_role":role})
        return user_data_with_roles
    
    async def get_relation_data(
                                self,
                                user_public_id: UUID,
                                project_public_id: UUID
                                ) -> Optional[UserProjectRelation]:
        return await self.get_by(user_public_id=user_public_id, project_public_id=project_public_id)
    
    async def count_project_users(
                                    self,
                                    project_public_id:  UUID
                                ) -> int:
        return await self.get_row_count_by(
            predicates=[UserProjectRelation.project_public_id==project_public_id]
            )

