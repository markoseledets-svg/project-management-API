from random import randint
import redis.asyncio as redis
from typing import Optional
import time
import json

from core.exceptions import ToManyRequestsError, AuthFailedError
from core.security import hash_data
from schemas.login_schemas import UserRegisterModel

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
    
    
    async def add_user_otp(self, user_data:UserRegisterModel) -> int:
        hased_password = hash_data(user_data.password.get_secret_value())
        otp = randint(100000, 999999)
        key = f"otp:users:{user_data.email}"
        json_data = json.dumps({
                                "email":user_data.email, 
                                "password":hased_password, 
                                "otp":otp
                                })
        await self.redis_client.setex(key, 180, json_data)
        return otp
    
    async def get_user_registration_data(
                                        self,
                                        email:str
                                        ) -> str:
        key = f"otp:users:{email}"
        user_data = await self.redis_client.get(key)
        if not user_data:
            raise AuthFailedError()
        return user_data
    
    async def delete_otp_data(
                                self,
                                email:str,
                                ) -> None:
        key = f"otp:users:{email}"
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
                                            payload:dict
                                          ) -> None:
        key =f"refresh-rotation:{refresh_token}"
        json_payload = json.dumps(payload)
        await self.redis_client.setex(key, 5, json_payload)
    
    async def check_refresh_for_retries(self, refresh_token:str) -> Optional[dict]:
        key =f"refresh-rotation:{refresh_token}"
        user_data = await self.redis_client.get(key)
        if user_data:
            return json.loads(user_data)
        return None
