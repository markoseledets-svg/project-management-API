import contextlib
from typing import Annotated, List
from fastapi import (
    APIRouter,
    Depends, 
    Response, 
    BackgroundTasks, 
    Header, 
    Cookie,
    Request
)
from uuid import UUID
from fastapi import Body
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from authlib.integrations.base_client import OAuthError

from app.api.dependencies.db_dependencies import ( 
    AuthServiceDep, 
    get_current_user
    )
from schemas.login_schemas import (
    UserGetModel,
    VerifyOTPModel, 
    UserRegisterModel,
    SessionsGetModel,
    ChangePasswordModel,
    AddPasswordModel,
    TokenResponseModel,
    ProviderResponseModel
)
from core.security import (
    delete_tokens_from_cookies, 
    set_tokens_to_cookies,
    set_restore_cookies,
    delete_restore_cookies
)
from core.exceptions import AuthFailedError, AppBaseError
from app.api.dependencies.redis_dependencies import rate_limit
from services.email_service import send_email, EmailType
from app.api.dependencies.identity_dependencies import (
    identity_from_ip,
    identity_from_otp,
    identity_from_login,
    identity_from_registration,
    identity_from_pwd_model
    )
from core.oauth_conf import oauth

router = APIRouter(tags=["Login"])

def _create_tokens_response(response: Response, auth_tokens: TokenResponseModel) -> None:
    if auth_tokens.is_restore:
        set_restore_cookies(response, auth_tokens.restore_token, auth_tokens.deletes_at)
    else:
        set_tokens_to_cookies(response, auth_tokens.access_token, auth_tokens.refresh_token)
     

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
    _create_tokens_response(response, tokens)

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
    set_tokens_to_cookies(response, tokens.access_token, tokens.refresh_token)

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
    response: Response,
    service: AuthServiceDep,
    restore_token: str|None = Cookie(default=None)
    ):
    if restore_token:
        delete_restore_cookies(response)
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

@router.get(
    "/oauth/google/auth",
    dependencies=[
        Depends(rate_limit("oauth-auth-ip", 180, 40, identity_from_ip))
    ]
)
async def google_auth_redirect(request: Request):
    redirect_url = request.url_for('process_google_callback_data')
    return await oauth.google.authorize_redirect(request, redirect_url, state='auth')

@router.get(
    "/oauth/google/link",
    dependencies=[
        Depends(rate_limit("oauth-link-ip", 180, 40, identity_from_ip)),
        Depends(rate_limit("oauth-link-user", 180, 10, identity_from_pwd_model))
    ]
)
async def google_link_redirect(request:Request, user: UserGetModel = Depends(get_current_user)):
    redirect_url = request.url_for('process_google_callback_data')
    return await oauth.google.authorize_redirect(request, redirect_url, state='link')

def _create_error_redirect(exc: OAuthError|AppBaseError) -> RedirectResponse:
    exc_response = RedirectResponse('http://localhost:8000/', status_code=303)
    description = (
        getattr(exc, 'detail', None) or 
        getattr(exc, 'description', None) or 
        getattr(exc, 'error', None) or 
        'OAuth authentication failed.')
    exc_response.set_cookie(key='oauth_error', value=description, httponly=False, max_age=15)
    return exc_response
 
@router.get(
    "/oauth/google/callback",
    dependencies=[
        Depends(rate_limit("oauth-callback-ip", 180, 40, identity_from_ip))
    ]
)
async def process_google_callback_data(
    request: Request,
    service: AuthServiceDep,
    access_token: str | None = Cookie(default=None),
    user_agent: Annotated[str, Header(alias="User-Agent")] = "Unknown Device"
    ):
    try:
        token = await oauth.google.authorize_access_token(request)
        form_data = token.get('userinfo')
        state = request.query_params.get('state')
        response = RedirectResponse("http://localhost:8000/app", status_code=303)
        if state == 'link':
            user = await get_current_user(service, access_token)
            await service.link_google(user, form_data)
        else: 
            auth_tokens = await service.auth_with_google(form_data, user_agent)
            _create_tokens_response(response, auth_tokens)
        return response
    except (OAuthError, AppBaseError) as exc:
        return _create_error_redirect(exc)

@router.get(
    "/oauth/github/auth",
    dependencies=[
        Depends(rate_limit("oauth-auth-ip", 180, 40, identity_from_ip))
    ]
)
async def github_oauth_auth(request: Request):
    redirect_url = request.url_for('process_github_callback_data')
    return await oauth.github.authorize_redirect(request, redirect_url, state='auth')

@router.get(
    "/oauth/github/link",
    dependencies=[
        Depends(rate_limit("oauth-link-ip", 180, 40, identity_from_ip)),
        Depends(rate_limit("oauth-link-user", 180, 10, identity_from_pwd_model))
    ]
)
async def github_oauth_link(request: Request, user: UserGetModel = Depends(get_current_user)):
    redirect_url = request.url_for('process_github_callback_data')
    return await oauth.github.authorize_redirect(request, redirect_url, state='link') 

@router.get(
    "/oauth/github/callback",
    dependencies=[
        Depends(rate_limit("oauth-callback-ip", 180, 40, identity_from_ip))
    ]
)
async def process_github_callback_data(
    request: Request,
    service: AuthServiceDep,
    access_token: str | None = Cookie(default=None),
    user_agent: Annotated[str, Header(alias="User-Agent")] = "Unknown Device"
    ):
    try:
        token = await oauth.github.authorize_access_token(request)
        user_resp = await oauth.github.get('user', token=token)
        user_data = user_resp.json()
        email_resp = await oauth.github.get('user/emails', token=token)
        email_data = email_resp.json()
        state=request.query_params.get('state')
        response=RedirectResponse('http://localhost:8000/app', status_code=303)
        if state == 'link':
            user = await get_current_user(service, access_token)
            await service.link_github(user, user_data)
        else: 
            auth_tokens = await service.auth_with_github(email_data, str(user_data['id']), user_agent)
            _create_tokens_response(response, auth_tokens)
        return response
    except (OAuthError, AppBaseError) as exc:
       return _create_error_redirect(exc)

@router.post(
    "/add-password",
    status_code=204,
    dependencies=[
        Depends(rate_limit("auth-addpwd-ip", 180, 40, identity_from_ip)),
        Depends(rate_limit("auth-addpwd-email", 180, 5, identity_from_pwd_model))
    ]
)
async def add_password_to_account(
    service: AuthServiceDep,
    background_task: BackgroundTasks,
    password: AddPasswordModel,
    user: UserGetModel = Depends(get_current_user)
    ):
    otp = await service.add_password(user, password.password.get_secret_value())
    background_task.add_task(send_email, otp, user.email, EmailType.PASSWORD_RESET)
    
@router.post(
    '/add-password/verify',
    status_code=204,
    dependencies=[
        Depends(rate_limit("auth-addpwd-otp-ip", 180, 40, identity_from_ip)),
        Depends(rate_limit("auth-addpwd-otp-email", 180, 5, identity_from_pwd_model))
    ]
)
async def verify_password_add_with_otp(
    service: AuthServiceDep,
    otp: int = Body(embed=True),
    user: UserGetModel = Depends(get_current_user)
    ):
    return await service.confirm_password_adding_with_otp(user.public_id, otp)

@router.get(
    '/providers', 
    response_model=List[ProviderResponseModel],
    dependencies=[
        Depends(rate_limit("auth-providers-ip", 60, 60, identity_from_ip))
    ]
)
async def get_providers_lst(
    service: AuthServiceDep,
    user: UserGetModel = Depends(get_current_user)
    ):
    return await service.get_users_auth_providers(user)

@router.delete(
    '/unlink-provider/{identity_public_id}', 
    status_code=204,
    dependencies=[
        Depends(rate_limit("auth-unlink-ip", 180, 40, identity_from_ip)),
        Depends(rate_limit("auth-unlink-user", 180, 10, identity_from_pwd_model))
    ]
)
async def unlink_provider(
    service: AuthServiceDep,
    identity_public_id: UUID,
    user: UserGetModel = Depends(get_current_user)
    ):
    return await service.unlink_identity(user, identity_public_id)
