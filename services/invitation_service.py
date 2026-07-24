from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from uuid6 import UUID
from typing import List

from repository.invitation_repo import InvitationRepository
from repository.user_repo import UserRepository
from repository.projects_repo import UserProjectRepository
from services.permission_check import PermissionService
from services.project_services import ProjectService
from schemas.invitation_schemas import InvitationNotificationModel, InvitationDashboardModel
from database.db_model import UserRole, InvitationModel, InvitationStatus
from core.exceptions import NotFoundError, ConflictError, GoneError

class InvitationService:
    def __init__(self, session:AsyncSession):
        self.session = session
        self.invitation_repo = InvitationRepository(session)
        self.permission_service = PermissionService(session)
        self.user_repo = UserRepository(session)
        self.user_project_repo = UserProjectRepository(session)
        self.project_service = ProjectService(session)

    async def get_user_invitations(
        self, 
        user_public_id: UUID,
        ) -> List[InvitationNotificationModel]:
        return await self.invitation_repo.get_users_invitations(user_public_id)

    async def get_project_invitation(
        self, 
        user_public_id:UUID,
        project_public_id:UUID
        ) -> List[InvitationDashboardModel]:
        await self.permission_service.verify_user_role(
            user_public_id,
            project_public_id,
            allowed_roles=(UserRole.ADMIN, UserRole.OWNER,)
        )
        return await self.invitation_repo.get_project_invitations(project_public_id)
    
    async def send_invitation(
        self,
        user_public_id:UUID,
        project_public_id:UUID,
        target_user_email:str,
        invitation_user_role:UserRole
        ) -> None:
        user_role = await self.permission_service.verify_user_role(
            user_public_id,
            project_public_id,
            allowed_roles=(UserRole.ADMIN, UserRole.OWNER,)
        )
        self.permission_service.verify_user_hierarchy(
            user_role,
            new_user_role=invitation_user_role
            )
        target_user_public_id = await self.user_repo.get_user_id_by_email(target_user_email)
        if not target_user_public_id:
            raise NotFoundError(detail="User with this email not found!")
        if user_public_id == target_user_public_id:
            raise ConflictError(detail="You cannot invite yourself to project!")
        relation_exists = await self.user_project_repo.get_user_role_request(
            target_user_public_id,
            project_public_id
        )
        if relation_exists:
            raise ConflictError(detail="User with this email already in project members!")
        new_invitation = InvitationModel(
            project_public_id=project_public_id,
            sender_public_id=user_public_id,
            target_user_public_id=target_user_public_id,
            user_role=invitation_user_role
        )
        try:
            self.invitation_repo.add(new_invitation)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(detail="User already have available invitation to this project!")

    async def check_invitation_availability(
        self,  
        invitation_public_id:UUID,
        user_public_id:UUID | None = None
        ) -> InvitationModel:
        invitation_data = await self.invitation_repo.get_invitation_by_id(invitation_public_id)
        if ((not invitation_data) 
        or (invitation_data.target_user_public_id != user_public_id 
        and user_public_id is not None)):
            raise NotFoundError()
        if invitation_data.status != InvitationStatus.PENDING:
            raise ConflictError(detail="Invitation isn't active!")
        expires_at = invitation_data.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise GoneError(detail="Invitation is expired!")
        return invitation_data

    async def accept_invitation(
        self, 
        user_public_id:UUID,
        invitation_public_id:UUID,
        ) -> None:
        invitation_data = await self.check_invitation_availability(invitation_public_id, user_public_id)
        updated = await self.invitation_repo.update_if_pending(
            invitation_public_id,
            InvitationStatus.ACCEPTED
        )
        if not updated:
            raise NotFoundError()
        try:
            self.project_service.add_user_to_project(
                invitation_data.project_public_id,
                user_public_id,
                invitation_data.user_role
            )
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(detail="User already is member of this project!")

    async def reject_invitation(
        self, 
        user_public_id:UUID,
        invitation_public_id:UUID
        ) -> None:
        await self.check_invitation_availability(
            invitation_public_id,
            user_public_id
        )
        updated = await self.invitation_repo.update_if_pending(
            invitation_public_id,
            InvitationStatus.REJECTED
        )
        if not updated:
            raise NotFoundError()
        await self.session.commit()

    async def revoke_invitation(
        self, 
        user_public_id:UUID,
        invitation_public_id:UUID,
        project_public_id: UUID
        ) -> None:
        user_role = await self.permission_service.verify_user_role(
            user_public_id,
            project_public_id,
            allowed_roles=(UserRole.ADMIN, UserRole.OWNER,)
        )
        invitation_data = await self.check_invitation_availability(
            invitation_public_id
        )
        if invitation_data.project_public_id != project_public_id:
            raise NotFoundError()
        self.permission_service.verify_user_hierarchy(
            user_role,
            new_user_role=invitation_data.user_role
        )
        updated = await self.invitation_repo.update_if_pending(
            invitation_public_id,
            InvitationStatus.REVOKED
        )
        if not updated:
            raise NotFoundError()
        await self.session.commit()
