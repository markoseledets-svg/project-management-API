import redis.asyncio as redis
from dotenv import load_dotenv
import os

REDIS_URL = os.getenv("REDIS_URL")

pool = redis.ConnectionPool.from_url(
    REDIS_URL, 
    decode_responses=True, 
    max_connections=50
    )

redis_client = redis.Redis(connection_pool=pool)