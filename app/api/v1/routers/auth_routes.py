import contextlib
from typing import Annotated, List
from fastapi import (
    APIRouter,
    Depends, 
    Response, 
    BackgroundTasks, 
    Header, 
    Cookie
)
from uuid import UUID
from fastapi import Body
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies.db_dependencies import ( 
    AuthServiceDep, 
    get_current_user
    )
from schemas.login_schemas import (
    UserGetModel,
    VerifyOTPModel, 
    UserRegisterModel,
    SessionsGetModel,
    ChangePasswordModel
)
from core.security import delete_tokens_from_cookies, set_tokens_to_cookies
from core.exceptions import AuthFailedError
from app.api.dependencies.redis_dependencies import rate_limit
from services.email_service import send_email, EmailType
from app.api.dependencies.identity_dependencies import (
    identity_from_ip,
    identity_from_otp,
    identity_from_login,
    identity_from_registration,
    identity_from_pwd_model
    )
router = APIRouter(tags=["Login"])


@router.post("/", 
    status_code=204,
    dependencies=[
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
    if tokens.is_restore:
        return JSONResponse(
            status_code=200,
            content={
                "status":"pending_restore",
                "deletes_at":tokens.deletes_at.isoformat() if tokens.deletes_at else None,
                "restore_token":tokens.restore_token
            }
        )
    else:
        set_tokens_to_cookies(response, tokens.access_token, tokens.refresh_token)

@router.post("/refresh", 
    status_code=204,
    dependencies=[
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
                            user_data:UserRegisterModel, 
                            background_task: BackgroundTasks,
                            service: AuthServiceDep
                            ):
    otp = await service.start_user_registration(user_data)
    background_task.add_task(send_email, otp, user_data.email)

@router.post("/verify-otp", 
    status_code=201,
    dependencies=[
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

@router.post("/logout", status_code=204)
async def logout_user(
                        response: Response,
                        service: AuthServiceDep,
                        access_token: str | None = Cookie(default=None),
                        refresh_token: str | None = Cookie(default=None)
                        ):
    with contextlib.suppress(AuthFailedError):
        await service.user_logout_process(access_token, refresh_token)
    
    delete_tokens_from_cookies(response)

@router.get("/active-sessions", response_model=List[SessionsGetModel])
async def get_user_sessions(
                            service: AuthServiceDep,
                            user: UserGetModel = Depends(get_current_user)
                            ):
    return await service.get_user_active_sessions(user.public_id)

@router.post("/logout-everywhere", status_code=204)
async def logout_user_everywhere(
    response: Response,
    service: AuthServiceDep,
    access_token: str | None = Cookie(default=None),
    refresh_token: str | None = Cookie(default=None)
    ):
    with contextlib.suppress(AuthFailedError):
        await service.logout_everywhere(access_token, refresh_token)
    delete_tokens_from_cookies(response)

@router.post("/logout-session/{token_public_id}", status_code=204)
async def logout_user_session(
    service: AuthServiceDep,
    token_public_id: UUID,
    user: UserGetModel = Depends(get_current_user)
    ):
    await service.logout_session(user.public_id, token_public_id)

@router.delete("/delete-account", status_code=204)
async def delete_user(
    service: AuthServiceDep,
    access_token: str | None = Cookie(default=None),
    refresh_token: str | None = Cookie(default=None)
    ):
    await service.delete_user_account(access_token, refresh_token)

@router.post("/restore-account", status_code=204)
async def restore_user_account(
    service: AuthServiceDep,
    restore_token: Annotated[str, Body(embed=True)]
    ):
    await service.verify_user_restore(restore_token)

@router.post(
    "/change-password", 
    status_code=204,
    dependencies= [
        Depends(rate_limit("auth-otp-email", 180, 5, identity_from_pwd_model))
        ]
    )  
async def change_user_password(
    service: AuthServiceDep,
    user_data: ChangePasswordModel,
    user: UserGetModel = Depends(get_current_user)
    ):
    await service.change_password(user, user_data)

@router.post(
    "/forgotten-password",
    status_code=204,
    dependencies=[
    Depends(rate_limit("auth-pwdc-ip", 180, 40, identity_from_ip)),
    Depends(rate_limit("auth-pwdc-email", 180, 5, identity_from_registration))
    ]
    )
async def forgotten_password_change(
    service: AuthServiceDep,
    background_task: BackgroundTasks,
    user_data: UserRegisterModel
    ):
    otp = await service.change_forgotten_password(user_data)
    background_task.add_task(send_email, otp, user_data.email, EmailType.PASSWORD_RESET)

@router.post(
    "/verify-password-change",
    status_code=204,
    dependencies=[
    Depends(rate_limit("auth-pwdc-otp-ip", 180, 40, identity_from_ip)),
    Depends(rate_limit("auth-pwdc-otp-email", 180, 5, identity_from_otp))
    ]
)
async def verify_change_forgotten_password(
    service: AuthServiceDep,
    user_data: VerifyOTPModel
    ):
    await service.verify_pwd_change_with_otp(user_data.otp, user_data.email)

