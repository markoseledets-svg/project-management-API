from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse

import redis.asyncio as redis
from core.config import settings
from core.security import decode_access_token
from core.exceptions import TooManyRequestsError
from services.redis_services import RedisServices

EXCLUDE_PATHS = {"/docs", "/redoc", "/openapi.json", "/health"}

class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    
    def __init__(self, app, client: redis.Redis | None = None):
        super().__init__(app)
        self.fallback_client = client

    async def dispatch(self, request: Request, call_next):
        if not settings.enable_global_rate_limit or request.url.path in EXCLUDE_PATHS or request.url.path.startswith('/api/v1/auth'):
            return await call_next(request)
        token = request.cookies.get('access_token')
        rate_key = None
        if token:
            try:
                payload = decode_access_token(token)
                request.state.user_data = payload
                rate_key = str(payload['user_public_id'])
            except Exception:
                pass
        if not rate_key:
            if not request.client or not request.client.host:
                return JSONResponse(status_code=400, content={"detail": "Cannot determine client address"})
            rate_key = request.client.host

        redis_client = getattr(request.app.state, "redis", None) or self.fallback_client
        if not redis_client:
            from database.redis_config import redis_client as default_redis
            redis_client = default_redis
        redis_services = RedisServices(redis_client)

        try:
            await redis_services.rate_limiter(rate_key, 'global', 60, 100)
        except TooManyRequestsError as e:
            return JSONResponse(
                status_code=e.status_code,
                content={'detail': e.detail},
                headers={'Retry-After': '60'}
            )
        return await call_next(request)


