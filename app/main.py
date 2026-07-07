from fastapi import FastAPI,  Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
from redis.exceptions import RedisError

from database.db_config import engine
from app.api.v1 import router
from app.api.v1.routers import frontend_routes
from utils.logger import logger
from core.exceptions import AppBaseError

load_dotenv()

IS_PRODUCTION = os.getenv("ENV") == "production"
CORS_ORIGINS = os.getenv("CORS_ORIGINS")
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

app = FastAPI(
    lifespan=lifespan,
    docs_url=None if IS_PRODUCTION  else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(SQLAlchemyError)
async def log_db_errors(request: Request, exc: SQLAlchemyError):
    logger.critical(f"Database error on path {request.method} {request.url.path}. error: {exc}")

    return JSONResponse(
        status_code = 503,
        content = {"message":"Service is temporarily unavailable. Please try again later."}
    )

@app.exception_handler(RedisError)
async def log_redis_errors(request: Request, exc: RedisError):
    logger.critical(f"Redis error on {request.method} {request.url.path}. error: {exc}")

    return JSONResponse(
        status_code = 503,
        content = {"message":"Service is temporarily unavailable. Please try again later."}
    )
    
@app.exception_handler(Exception)
async def api_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error on {request.method} {request.url.path} error: {exc}")

    return JSONResponse(
        status_code = 500,
        content = {"message":"Ops, something went wrong."}
    )

@app.exception_handler(AppBaseError)
async def http_errors_handler(request: Request, exc: AppBaseError):
    logger.warning(f"Api exc occured:{exc.status_code}:{exc.detail} on path {request.method} {request.url.path}.")
    return JSONResponse(
        status_code = exc.status_code,
        content = {"detail":exc.detail}
    )

app.include_router(frontend_routes.router)
app.include_router(router.router_v1)
