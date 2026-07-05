from typing import Annotated
from fastapi import APIRouter, Depends, Request, Body, BackgroundTasks, Header
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies.db_dependencies import ( 
    AuthServiceDep, 
    get_current_user, 
    oauth2_scheme
    )
from schemas.login_schemas import UserPostModel, UserGetModel, VerifyOTPModel
from app.api.dependencies.redis_dependencies import rate_limit
from services.email_service import send_email
from app.api.dependencies.identity_dependencies import (
    identity_from_ip,
    identity_from_otp,
    identity_from_login,
    identity_from_registration
    )

router = APIRouter(tags=["Login"])


@router.post("/", dependencies=[
    Depends(rate_limit("auth-login-ip", 180, 40, identity_from_ip)),
    Depends(rate_limit("auth-login-email-fast", 180, 5, identity_from_login)),
    Depends(rate_limit("auth-login-email-medium", 900, 10, identity_from_login)),
    Depends(rate_limit("auth-login-email-slow", 3600, 20, identity_from_login))
    ])
async def login_for_access_token(
                                request:Request,
                                auth_service: AuthServiceDep, 
                                form_data: OAuth2PasswordRequestForm = Depends(),
                                user_agent: Annotated[str, Header(alias="User-Agent")] = "Unknown Device"
                                ):
    return await auth_service.user_login_process(user_agent,form_data)

@router.post("/refresh", dependencies=[
    Depends(rate_limit("auth-refresh-ip", 60, 100, identity_from_ip))
    ])
async def refresh_access_token(
                               auth_service: AuthServiceDep, 
                               refresh_token: str = Body(..., embed=True),
                               user_agent: Annotated[str, Header(alias="User-Agent")] = "Unknown Device"
                               ):
    return await auth_service.rotate_refresh_token(refresh_token, user_agent)

@router.post("/register", dependencies=[
    Depends(rate_limit("auth-register-ip", 3600, 40, identity_from_ip)),
    Depends(rate_limit("auth-register-email", 3600, 3, identity_from_registration))
    ])
async def register_new_user(
                            user_data:UserPostModel, 
                            background_task: BackgroundTasks,
                            service: AuthServiceDep
                            ):
    otp = await service.start_user_registration(user_data)
    background_task.add_task(send_email, otp, user_data.email)

@router.post("/verify-otp", dependencies=[
    Depends(rate_limit("auth-otp-ip", 180, 40, identity_from_ip)),
    Depends(rate_limit("auth-otp-email", 180, 5, identity_from_otp))
    ])
async def verify_registration(
                                service: AuthServiceDep,
                                user_data: VerifyOTPModel
                                ):
    await service.verify_user_registration(user_data.email, user_data.otp)

@router.get("/me", response_model = UserGetModel)
async def get_me(current_user: UserGetModel = Depends(get_current_user)):
    return current_user

@router.post("/logout")
async def logout_user(
                        service: AuthServiceDep,
                        user_access_token:str = Depends(oauth2_scheme),
                        user_refresh_token:str = Body(..., embed=True),
                        ):
    return await service.user_logout_process(
        user_access_token,
        user_refresh_token
    )
                