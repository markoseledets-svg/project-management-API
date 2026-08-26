from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from schemas.login_schemas import UserPostModel, VerifyOTPModel, UserGetModel
from app.api.dependencies.db_dependencies import get_current_user

def identity_from_login(form_data: OAuth2PasswordRequestForm = Depends()) -> str:
    return form_data.username.lower()

def identity_from_registration(user_data: UserPostModel) -> str:
    return user_data.email.lower()

def identity_from_otp(user_data:VerifyOTPModel) -> str:
    return user_data.email.lower()

def identity_from_ip(request: Request) -> str:
    raw_ip = request.headers.get("x-forwarded-for", request.client.host)
    return raw_ip.split(",")[0].strip()

def identity_from_pwd_model(user: UserGetModel = Depends(get_current_user)) -> str:
    return user.email.lower()  
