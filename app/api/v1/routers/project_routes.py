from fastapi import APIRouter, Depends
from typing import List
import uuid

from database.db_model import ProjectStatus
from app.api.dependencies.db_dependencies import ProjectServiceDep, get_current_user
from schemas.project_schemas import ProjectWithRoleGetModel, ProjectPostModel, ProjectGetModel, ProjectUpdateModel, PostNewRelation
from schemas.login_schemas import UserGetModel

router = APIRouter(tags=["Projects"])

@router.get("/", response_model=List[ProjectWithRoleGetModel])
async def get_user_projects(
                            service: ProjectServiceDep,
                            user: UserGetModel = Depends(get_current_user)
                            ):
    return await service.get_curr_user_projects(user.public_id)

@router.post("/add")
async def add_project(
                        service: ProjectServiceDep,
                        project_data:ProjectPostModel,
                        user: UserGetModel = Depends(get_current_user)
                    ):
    return await service.add_new_project(project_data,user.public_id)

@router.patch("/update/{project_public_id}", response_model=ProjectGetModel)
async def update_project_by_id(
                                service: ProjectServiceDep,
                                project_public_id:uuid.UUID,
                                project_data: ProjectUpdateModel,
                                user: UserGetModel = Depends(get_current_user)
                            ):
    return await service.update_project(
                                        user.public_id,
                                        project_public_id,
                                        project_data
                                        )
@router.patch("/change-status/{project_public_id}", response_model=ProjectGetModel)
async def change_status(
                        service: ProjectServiceDep,
                        project_public_id: uuid.UUID,
                        project_new_status: ProjectStatus,
                        user: UserGetModel = Depends(get_current_user)
                        ):
    return await service.change_project_status(
                                                user.public_id,
                                                project_public_id,
                                                project_new_status
                                                )
@router.delete("/delete/{project_public_id}")
async def delete_project_by_id(
                                service: ProjectServiceDep,
                                project_public_id: uuid.UUID,
                                user: UserGetModel = Depends(get_current_user)
                                ):
    return await service.delete_project(project_public_id,user.public_id)

@router.post("/add-user/{project_public_id}")
async def add_user_to_project(
                                service: ProjectServiceDep,
                                project_public_id: uuid.UUID,
                                new_relation_data: PostNewRelation, 
                                user: UserGetModel = Depends(get_current_user)
                            ):
    return await service.add_user_to_project(
                                            project_public_id,
                                            new_relation_data,
                                            user.public_id
                                            )