import redis.asyncio as redis
from redis.exceptions import RedisError
from typing import Optional, Callable, TypeVar, Awaitable, Type
from pydantic import TypeAdapter, ValidationError
import time
import json
import random
from functools import lru_cache

from core.exceptions import ToManyRequestsError, AuthFailedError
from schemas.login_schemas import TokenResponseModel
from utils.logger import logger

T = TypeVar('T') 

class RedisServices:
    def __init__ (self, redis_client:redis.Redis):
        self.redis_client = redis_client
    
    async def rate_limiter(
                            self, 
                            rate_limit_data: str,
                            prefix:str,
                            window_size: int,
                            requests_count: int
                            ) -> None:
        limit_pipeline = self.redis_client.pipeline()
        limit_key = f"ratelimit:{prefix}:{rate_limit_data}"
        timestamp = time.time()
        window = timestamp - window_size
        id = f"{timestamp}:{rate_limit_data}"
        limit_pipeline.zadd(limit_key, {id:timestamp})
        limit_pipeline.zremrangebyscore(limit_key, "-inf", window)
        limit_pipeline.zcard(limit_key)
        limit_pipeline.expire(limit_key, window_size)
        result = await limit_pipeline.execute()
        if result[2] > requests_count:
            raise ToManyRequestsError()
    
    
    async def add_user_otp(self, user_key_value: str, values_dict: dict) -> None:
        key = f"otp:{user_key_value}"
        json_data = json.dumps(values_dict)
        await self.redis_client.setex(key, 180, json_data)
    
    async def get_user_otp_data(
                                        self,
                                        user_key_value:str
                                        ) -> str:
        key = f"otp:{user_key_value}"
        user_data = await self.redis_client.get(key)
        if not user_data:
            raise AuthFailedError()
        return user_data
    
    async def delete_otp_data(
                                self,
                                user_key_value:str,
                                ) -> None:
        key = f"otp:{user_key_value}"
        await self.redis_client.delete(key)
    
    async def save_banned_access_token(
                                        self,
                                        user_token: str,
                                        exp: float
                                        ) -> None:
        key = f"tokens:banned:{user_token}"
        token_ttl = int(exp - time.time())
        if token_ttl <= 0:
            return
        await self.redis_client.setex(key, token_ttl, "1")

        
    async def check_banned_tokens(self, user_token:str) -> bool:
        key = f"tokens:banned:{user_token}"
        return await self.redis_client.exists(key)
    
    async def save_token_data_for_retries(
                                            self, 
                                            refresh_token:str, 
                                            payload:TokenResponseModel
                                          ) -> None:
        key =f"refresh-rotation:{refresh_token}"
        json_payload = json.dumps(payload.model_dump(mode='json'))
        await self.redis_client.setex(key, 5, json_payload)
    
    async def check_refresh_for_retries(self, refresh_token:str) -> Optional[dict]:
        key =f"refresh-rotation:{refresh_token}"
        user_data = await self.redis_client.get(key)
        if user_data:
            return json.loads(user_data)
        return None
    
    @staticmethod
    @lru_cache(maxsize=None)
    def _adapter(tp:type) -> TypeAdapter:
        return TypeAdapter(tp)
    
    async def get_or_set_cache(
        self,
        key: str,
        tp:Type[T],
        db_loader: Callable[[], Awaitable[T]],
        cache_ttl: int,
        ) -> T:
        cache_key = f'cache:{key}' if not key.startswith('cache:') else key
        adapter = self._adapter(tp)
        try:
            data = await self.redis_client.get(cache_key)
        except RedisError:
            logger.error(f'Cache read redis error', exc_info=True)
            return await db_loader()
        if data is not None:
            try:
                return adapter.validate_json(data)
            except ValidationError:
                await self.redis_client.delete(cache_key)
                logger.warning('Cache validation error', exc_info=True)
        data = await db_loader()
        if data is None:
            return data
        try:
            jitter = random.randint(0, cache_ttl//10)
            await self.redis_client.set(cache_key, adapter.dump_json(data), ex=cache_ttl + jitter)
        except RedisError:
            logger.error('Cache set redis error', exc_info=True)
        return data
    
    async def invalidate_cache(
        self,
        *keys: str
        ) -> None:
        try:
            if keys:
                formatted_keys = [f'cache:{k}' if not k.startswith('cache:') else k for k in keys]
                await self.redis_client.delete(*formatted_keys)
        except RedisError as exc:
            logger.error('Cache invalidation redis error', exc_info=True)
    
    async def bump_version(self, key: str) -> None:
        try:
            formated_key = key if key.startswith('cache:') else f'cache:{key}'
            pipe = self.redis_client.pipeline()
            pipe.incr(formated_key)
            pipe.expire(formated_key, 259200, nx=True)
            await pipe.execute()
        except RedisError:
            logger.error('Cache version bump error', exc_info=True)

    async def get_version(self, key:str) -> int:
        try:
            formated_key = key if key.startswith('cache:') else f'cache:{key}'
            ver = await self.redis_client.get(formated_key)
            return int(ver) if ver else 0
        except RedisError:
            logger.error('Cache version get error', exc_info=True)
        return 0
    
