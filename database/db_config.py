from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from core.config import settings

DB_URL = settings.database_url
POOL_SIZE = settings.pool_size
POOL_OVERFLOW = settings.max_overflow
POOL_TIMEOUT = settings.pool_timeout

engine = create_async_engine(
    DB_URL,
    echo = False,
    pool_size = POOL_SIZE,
    max_overflow = POOL_OVERFLOW,
    pool_timeout = POOL_TIMEOUT,
    pool_recycle = 1800,
    pool_pre_ping = True
    )

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
