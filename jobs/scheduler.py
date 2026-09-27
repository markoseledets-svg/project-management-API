from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from jobs.cleanup_jobs import expire_invitations_job, daily_cleanup_job

from utils.logger import logger

scheduler = AsyncIOScheduler(timezone="UTC")

def start_cleanup():
    scheduler.add_job(
        expire_invitations_job,
        trigger=IntervalTrigger(minutes=30),
        id='expire_invitations',
        max_instances=1,
        replace_existing=True,
        coalesce=True
    )
    scheduler.add_job(
        daily_cleanup_job,
        trigger=CronTrigger(hour=3, minute=0),
        id='daily_cleanup',
        max_instances=1,
        replace_existing=True,
        coalesce=True
    )
    scheduler.start()
    logger.info('[CRON] APScheduler succesfully started with cleanup jobs.')

def stop_cleanup():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info('[CRON] APScheduler stopped.')