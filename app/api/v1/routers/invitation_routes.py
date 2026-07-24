from fastapi import APIRouter, Depends
from uuid import UUID
from typing import List

from app.api.dependencies.db_dependencies import InvitationServiceDep, get_current_user
from schemas.login_schemas import UserGetModel
from schemas.invitation_schemas import (
    InvitationPostModel,
    InvitationDashboardModel,
    InvitationNotificationModel
    )

router = APIRouter(tags=["invitations"])

@router.post("/send-invitation/{project_public_id}", status_code=201)
async def send_new_invitation(
    invitation_data: InvitationPostModel,
    project_public_id: UUID,
    service: InvitationServiceDep,
    user: UserGetModel = Depends(get_current_user)
    ):
    return await service.send_invitation(
        user.public_id,
        project_public_id,
        invitation_data.email,
        invitation_data.user_role
    )

@router.get("/invitations-dashboard/{project_public_id}", response_model=List[InvitationDashboardModel])
async def get_invitation_dashboard(
    project_public_id:UUID,
    service: InvitationServiceDep,
    user: UserGetModel = Depends(get_current_user)
    ):
    return await service.get_project_invitation(
        user.public_id,
        project_public_id
    )

@router.get("/invitations/", response_model=List[InvitationNotificationModel])
async def get_curr_user_invitations(
    service:InvitationServiceDep,
    user: UserGetModel = Depends(get_current_user)
    ):
    return await service.get_user_invitations(user.public_id)

@router.patch("/accept-invitation/{invitation_public_id}", status_code=204)
async def invitation_accept(
    invitation_public_id: UUID,
    service: InvitationServiceDep,
    user: UserGetModel = Depends(get_current_user)
    ):
    return await service.accept_invitation(
        user.public_id,
        invitation_public_id
    )

@router.patch("/reject-invitation/{invitation_public_id}", status_code=204)
async def invitation_reject(
    invitation_public_id: UUID,
    service: InvitationServiceDep,
    user: UserGetModel = Depends(get_current_user)
    ):
    return await service.reject_invitation(
        user.public_id,
        invitation_public_id
    )

@router.patch("/revoke-invitation/{project_public_id}/{invitation_public_id}", status_code=204)
async def invitation_revoke(
    project_public_id:UUID,
    invitation_public_id: UUID,
    service: InvitationServiceDep,
    user: UserGetModel = Depends(get_current_user)
    ):
    return await service.revoke_invitation(
        user.public_id,
        invitation_public_id,
        project_public_id
    )