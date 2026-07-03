import redis.asyncio as redis
from fastapi import Depends
from typing import Annotated, Callable

from database.redis_config import pool
from services.redis_services import RedisServices

async def get_redis():
    async with redis.Redis(connection_pool=pool) as redis_client:
        yield redis_client

RedisClient = Annotated[redis.Redis, Depends(get_redis)]

async def get_redis_service(client:RedisClient) -> RedisServices:
    return RedisServices(client)

IdentityGetter = Callable[..., str]

def rate_limit(tag:str, window: int, requests: int, identity_getter:IdentityGetter):
    async def _dependency(
        identity: str = Depends(identity_getter),
        client: RedisServices = Depends(get_redis_service)
        ):
        await client.rate_limiter(identity, tag, window, requests)
    return _dependency