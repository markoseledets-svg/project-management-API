from sqlalchemy import select, update
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid6 import UUID
from datetime import datetime, timezone
from repository.base_repo import BaseRepository
from database.db_model import InvitationModel, InvitationStatus, UserModel, ProjectModel
from schemas.invitation_schemas import InvitationDashboardModel, InvitationNotificationModel
from schemas.filter_schemas import InvitationFilters

class InvitationRepository(BaseRepository[InvitationModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(InvitationModel, session)
    
    async def get_invitation_by_id(self, invitation_public_id:UUID) -> Optional[InvitationModel]:
        return await self.get_by(invitation_public_id=invitation_public_id)

    def _build_predicates(
        self,
        project_public_id: UUID,
        filters: InvitationFilters
    ) -> list:
        predicates = [InvitationModel.project_public_id == project_public_id]
        if filters.status is not None:
            predicates.append(InvitationModel.status == filters.status)
        return predicates

    async def get_users_invitations(
        self, 
        user_public_id: UUID,
        page: int,
        limit: int
    ) -> Optional[List[InvitationNotificationModel]]:
        SenderModel = aliased(UserModel)
        invitation_obj = await self.session.execute(
            select(
                InvitationModel.invitation_public_id,
                InvitationModel.status,
                InvitationModel.user_role,
                InvitationModel.sent_at,
                InvitationModel.expires_at,
                SenderModel.email.label("sender_email"),
                ProjectModel.project_name
            )
            .join(SenderModel, InvitationModel.sender_public_id == SenderModel.public_id)
            .join(ProjectModel, InvitationModel.project_public_id == ProjectModel.project_public_id)
            .where(
                    InvitationModel.target_user_public_id == user_public_id, 
                    InvitationModel.status == InvitationStatus.PENDING
            )
            .order_by(InvitationModel.sent_at.desc())
            .limit(limit)
            .offset((page - 1) * limit)
        )
        return invitation_obj.mappings().all()

    async def count_users_invitations(self, user_public_id: UUID) -> int:
        return await self.get_row_count_by(
            predicates = [
            InvitationModel.target_user_public_id==user_public_id,
            InvitationModel.status==InvitationStatus.PENDING
            ]
        )
    
    async def get_project_invitations(
        self, 
        project_public_id: UUID,
        page: int,
        limit: int,
        filters: InvitationFilters
    ) -> Optional[List[InvitationDashboardModel]]:
        SenderModel = aliased(UserModel)
        TargetUser = aliased(UserModel)
        predicates = self._build_predicates(project_public_id, filters)
        invitation_obj = await self.session.execute(
            select(
                InvitationModel.invitation_public_id,
                InvitationModel.status,
                InvitationModel.user_role,
                InvitationModel.sent_at,
                InvitationModel.expires_at,
                SenderModel.email.label("sender_email"),
                TargetUser.email.label("invited_user_email")
            )
            .join(SenderModel, SenderModel.public_id == InvitationModel.sender_public_id)
            .join(TargetUser, TargetUser.public_id == InvitationModel.target_user_public_id)
            .where(*predicates)
            .order_by(InvitationModel.sent_at.desc())
            .limit(limit)
            .offset((page - 1) * limit)
        )
        return invitation_obj.mappings().all()

    async def count_project_invitations(self, project_public_id: UUID, filters: InvitationFilters) -> int:
        return await self.get_row_count_by(
            predicates=self._build_predicates(project_public_id, filters)
            )

    async def update_if_pending(
        self, 
        invitation_public_id:UUID, 
        new_status:InvitationStatus
        ) -> bool:
        result = await self.session.execute(update(InvitationModel)
        .where(InvitationModel.invitation_public_id == invitation_public_id,
               InvitationModel.status == InvitationStatus.PENDING)
               .values(status = new_status, resolved_at = datetime.now(timezone.utc)))
        return result.rowcount > 0
