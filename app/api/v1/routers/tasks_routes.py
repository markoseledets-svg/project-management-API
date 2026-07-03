from fastapi import APIRouter, Depends
import uuid

from schemas.task_schemas import PostTaskModel,UpdateTaskModel
from schemas.login_schemas import UserGetModel
from app.api.dependencies.db_dependencies import get_current_user, TaskServiceDep
router = APIRouter(tags=["Tasks"])

@router.post("/")
async def add_task(
                    task_data: PostTaskModel,
                    project_public_id: uuid.UUID,
                    service: TaskServiceDep, 
                    user: UserGetModel = Depends(get_current_user)
                    ):
    return await service.add_new_task(task_data, user.public_id, project_public_id)

@router.get("/")
async def get_user_project_tasks(
                        service: TaskServiceDep,
                        project_public_id: uuid.UUID,
                        user: UserGetModel = Depends(get_current_user)
                        ):
    return await service.get_curr_user_project_tasks(user.public_id, project_public_id)

@router.patch("/{task_public_id}")
async def update_user_task(
                            project_public_id: uuid.UUID,
                            task_public_id: uuid.UUID,
                            update_data: UpdateTaskModel,
                            service: TaskServiceDep,
                            user: UserGetModel = Depends(get_current_user)
                            ):
    return await service.update_task(
                                        update_data,
                                        task_public_id,
                                        user.public_id,
                                        project_public_id
                                    )

@router.patch("/{task_public_id}/change-status")
async def change_task_status(
                            project_public_id: uuid.UUID,
                            task_public_id: uuid.UUID,
                            service: TaskServiceDep,
                            user: UserGetModel = Depends(get_current_user)
                            ):
    return await service.change_completed_status(user.public_id, task_public_id, project_public_id)

@router.delete("/{task_public_id}")
async def delete_user_task(
                            task_public_id: uuid.UUID,
                            project_public_id: uuid.UUID,
                            service: TaskServiceDep,
                            user: UserGetModel = Depends(get_current_user)
                            ):
    return await service.delete_task(task_public_id, user.public_id, project_public_id)
