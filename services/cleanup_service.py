from repository.cleanup_repo import CleanUpRepository
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Callable, Awaitable

class CleanUpService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cleanup_repo = CleanUpRepository(session)
    
    async def _drain_batches(
        self,
        cleanup_func: Callable[[int], Awaitable[int]],
        batch_size: int = 1000,
        max_batches: int = 20
        ) -> int:
        total_rows_affected = 0
        for _ in range(max_batches):
            row_count = await cleanup_func(batch_size)
            total_rows_affected += row_count
            await self.session.commit()
            if row_count < batch_size:
                break
        return total_rows_affected

    async def daily_cleanup(self) -> dict:
        deleted_users = await self._drain_batches(self.cleanup_repo.clean_deleted_user_accounts)
        deleted_tokens = await self._drain_batches(self.cleanup_repo.delete_expired_token_records)
        deleted_invitations = await self._drain_batches(self.cleanup_repo.delete_old_rejected_invitations)
        return {
            'deleted_users': deleted_users,
            'deleted_tokens': deleted_tokens,
            'deleted_invitations': deleted_invitations
        }
    
    async def expire_invitations(self) -> int:
        expired_invitations = await self._drain_batches(self.cleanup_repo.expire_invitations, 250)
        return expired_invitations