from sqlalchemy import select
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from database.db_model import (
    UserModel,
    InvitationModel,
    InvitationStatus,
    RefreshTokenModel,
    TaskModel,
)

class CleanUpRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def expire_invitations(self, row_limit: int) -> int:
        subquery = (
            select(InvitationModel.invitation_public_id)
            .where(
                InvitationModel.expires_at <= datetime.now(timezone.utc),
                InvitationModel.status == InvitationStatus.PENDING
                )
            .limit(row_limit)
            .scalar_subquery()
            )

        result = await self.session.execute(
            update(InvitationModel)
            .where(InvitationModel.invitation_public_id.in_(subquery))
            .values(status=InvitationStatus.EXPIRED)
        )
        return result.rowcount
    
    async def delete_expired_token_records(self, row_limit:int) -> int:
        subquery = (
            select(RefreshTokenModel.token_public_id)
            .where(RefreshTokenModel.expired_at <= datetime.now(timezone.utc))
            .limit(row_limit)
            .scalar_subquery()
        )

        result = await self.session.execute(
            delete(RefreshTokenModel)
            .where(RefreshTokenModel.token_public_id.in_(subquery))
        )
        return result.rowcount

    async def clean_deleted_user_accounts(self, row_limit: int) -> int:
        subquery = (
            select(UserModel.public_id)
            .where(
                UserModel.deletes_at.is_not(None),
                UserModel.deletes_at <= datetime.now(timezone.utc)
                )
            .limit(row_limit)
            .scalar_subquery()
        )
        
        await self.session.execute(
            update(TaskModel)
            .where(TaskModel.assignee_id.in_(subquery))
            .values(assignee_id=None)
        )

        result = await self.session.execute(
            delete(UserModel)
            .where(UserModel.public_id.in_(subquery))
        )
        return result.rowcount

    async def delete_old_rejected_invitations(self, row_limit: int) -> int:
        threshold = datetime.now(timezone.utc) - timedelta(days=30)
        subquery = (
            select(InvitationModel.invitation_public_id)
            .where(
                InvitationModel.sent_at <= threshold,
                InvitationModel.status.in_([
                    InvitationStatus.REJECTED,
                    InvitationStatus.REVOKED,
                    InvitationStatus.EXPIRED,
                ])
            )
            .limit(row_limit)
            .scalar_subquery()
        )
        
        result = await self.session.execute(
            delete(InvitationModel)
            .where(InvitationModel.invitation_public_id.in_(subquery))
        )
        return result.rowcount
