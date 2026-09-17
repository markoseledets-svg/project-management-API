import redis.asyncio as redis
from typing import Optional
import time
import json

from core.exceptions import ToManyRequestsError, AuthFailedError
from schemas.login_schemas import TokenResponseModel

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
        key = f"otp:users:{user_key_value}"
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
