import contextlib
from typing import Annotated
from fastapi import (
    APIRouter,
    Depends, 
    Response, 
    BackgroundTasks, 
    Header, 
    Cookie
)
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies.db_dependencies import ( 
    AuthServiceDep, 
    get_current_user
    )
from schemas.login_schemas import UserPostModel, UserGetModel, VerifyOTPModel
from core.security import delete_tokens_from_cookies, set_tokens_to_cookies
from core.exceptions import AuthFailedError
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
                                response: Response,
                                auth_service: AuthServiceDep, 
                                form_data: OAuth2PasswordRequestForm = Depends(),
                                user_agent: Annotated[str, Header(alias="User-Agent")] = "Unknown Device"
                                ):
    tokens = await auth_service.user_login_process(user_agent,form_data)
    set_tokens_to_cookies(response, tokens["access_token"], tokens["refresh_token"])

@router.post("/refresh", dependencies=[
    Depends(rate_limit("auth-refresh-ip", 60, 100, identity_from_ip))
    ])
async def refresh_access_token(
                               response: Response,
                               auth_service: AuthServiceDep, 
                               refresh_token: str | None = Cookie(default=None),
                               user_agent: Annotated[str, Header(alias="User-Agent")] = "Unknown Device"
                               ):
    tokens = await auth_service.rotate_refresh_token(refresh_token, user_agent)
    set_tokens_to_cookies(response, tokens["access_token"], tokens["refresh_token"])

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
                        response: Response,
                        service: AuthServiceDep,
                        access_token: str | None = Cookie(default=None),
                        refresh_token: str | None = Cookie(default=None)
                        ):
    with contextlib.suppress(AuthFailedError):
        await service.user_logout_process(access_token, refresh_token)
    
    delete_tokens_from_cookies(response)
                