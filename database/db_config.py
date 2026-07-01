from sqlalchemy.ext.asyncio import create_async_engine
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
POOL_SIZE = os.getenv("POOL_SIZE")
POOL_OVERFLOW = os.getenv("POOL_OVERFLOW")
POOL_TIMEOUT = os.getenv("POOL_TIMEOUT")

engine = create_async_engine(
    DB_URL,
    echo = False,
    pool_size = int(POOL_SIZE) if POOL_SIZE and POOL_SIZE.isdigit() else 15,
    max_overflow = int(POOL_OVERFLOW) if POOL_OVERFLOW and POOL_OVERFLOW.isdigit() else 15,
    pool_timeout = int(POOL_TIMEOUT) if POOL_TIMEOUT and POOL_TIMEOUT.isdigit() else 30,
    pool_recycle = 1800,
    pool_pre_ping = True
    )
