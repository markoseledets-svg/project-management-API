import redis.asyncio as redis
from core.config import settings

REDIS_URL = settings.redis_url

pool = redis.ConnectionPool.from_url(
    REDIS_URL, 
    decode_responses=True, 
    max_connections=settings.redis_max_connections
)

redis_client = redis.Redis(connection_pool=pool)