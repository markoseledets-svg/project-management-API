from services.cleanup_service import CleanUpService
from database.db_config import async_session_maker
from utils.logger import logger

async def expire_invitations_job():
    try:
        async with async_session_maker() as session:
            service = CleanUpService(session)
            count = await service.expire_invitations()
        logger.info(f'[CRON] Successfully expired {count} invitations.')
    except Exception as exc:
        logger.error(f'[CRON] Error on expiring invitations: {exc}')

async def daily_cleanup_job():
    try:
        async with async_session_maker() as session:
            service = CleanUpService(session)
            count_dict = await service.daily_cleanup()
        logger.info(
            f"[CRON] Daily cleanup successfully completed: "
            f"users={count_dict['deleted_users']}, "
            f"tokens={count_dict['deleted_tokens']}, "
            f"invitations={count_dict['deleted_invitations']}"
        )
    except Exception as exc:
        logger.error(f'[CRON] Error on daily cleanup: {exc}')