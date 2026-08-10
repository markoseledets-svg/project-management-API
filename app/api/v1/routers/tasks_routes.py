from fastapi import APIRouter, Depends, Body
import uuid
from typing import List

from schemas.task_schemas import PostTaskModel,UpdateTaskModel, TaskWithAssigneeModel, GetTaskModel
from schemas.login_schemas import UserGetModel
from app.api.dependencies.db_dependencies import get_current_user, TaskServiceDep
router = APIRouter(tags=["Tasks"])

@router.post("/", status_code=201)
async def add_task(
                    task_data: PostTaskModel,
                    project_public_id: uuid.UUID,
                    service: TaskServiceDep, 
                    user: UserGetModel = Depends(get_current_user)
                    ):
    return await service.add_new_task(task_data, user.public_id, project_public_id)

@router.get("/", response_model=List[TaskWithAssigneeModel])
async def get_tasks_with_assignee(
                        service: TaskServiceDep,
                        project_public_id: uuid.UUID,
                        user: UserGetModel = Depends(get_current_user)
                        ):
    return await service.get_curr_user_project_tasks(user.public_id, project_public_id)

@router.patch("/{task_public_id}", response_model=GetTaskModel)
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

@router.delete("/{task_public_id}", status_code=204)
async def delete_user_task(
                            task_public_id: uuid.UUID,
                            project_public_id: uuid.UUID,
                            service: TaskServiceDep,
                            user: UserGetModel = Depends(get_current_user)
                            ):
    return await service.delete_task(task_public_id, user.public_id, project_public_id)

@router.patch("/{task_public_id}/status/review", response_model=GetTaskModel)
async def change_status_to_review(
    task_public_id: uuid.UUID,
    project_public_id: uuid.UUID,
    service: TaskServiceDep,
    user: UserGetModel = Depends(get_current_user)
    ):
    return await service.send_task_to_review(
        user.public_id,
        task_public_id,
        project_public_id
    )

@router.patch("/{task_public_id}/status/cancel-review", response_model=GetTaskModel)
async def cancel_review_status(
    task_public_id: uuid.UUID,
    project_public_id: uuid.UUID,
    service: TaskServiceDep,
    user: UserGetModel = Depends(get_current_user)
    ):
    return await service.cancel_task_review_status(
        user.public_id,
        task_public_id,
        project_public_id
    )

@router.patch("/{task_public_id}/status/completed", response_model=GetTaskModel)
async def change_status_to_completed(
    task_public_id: uuid.UUID,
    project_public_id: uuid.UUID,
    service: TaskServiceDep,
    user: UserGetModel = Depends(get_current_user)
    ):
    return await service.change_status_to_completed(
        user.public_id,
        task_public_id,
        project_public_id
    )

@router.patch("/{task_public_id}/status/cancel-completed", response_model=GetTaskModel)
async def cancel_completed_status(
    task_public_id: uuid.UUID,
    project_public_id: uuid.UUID,
    service: TaskServiceDep,
    user: UserGetModel = Depends(get_current_user)
    ):
    return await service.cancel_completed_status(
        user.public_id,
        task_public_id,
        project_public_id
    )


@router.patch("/{task_public_id}/assignee/{target_user_public_id}", response_model=GetTaskModel)
async def assign_user_to_task(
    task_public_id: uuid.UUID,
    project_public_id: uuid.UUID,
    service: TaskServiceDep,
    target_user_public_id: uuid.UUID,
    user: UserGetModel = Depends(get_current_user)  
    ):
    return await service.assign_user_to_task(
        user.public_id,
        task_public_id,
        project_public_id,
        target_user_public_id
    )

@router.delete("/{task_public_id}/assignee", response_model=GetTaskModel)
async def delete_task_assignee(
    task_public_id: uuid.UUID,
    project_public_id: uuid.UUID,
    service: TaskServiceDep,
    user: UserGetModel = Depends(get_current_user)
    ):
    return await service.delete_task_assignee(
        user.public_id,
        project_public_id,
        task_public_id
        )

@router.post("/{task_public_id}/self-assign", response_model=GetTaskModel)
async def take_task(
    task_public_id: uuid.UUID,
    project_public_id: uuid.UUID,
    service: TaskServiceDep,
    user: UserGetModel = Depends(get_current_user)
    ):
    return await service.user_self_assign_to_task(
        user.public_id,
        task_public_id,
        project_public_id
    )

