from fastapi import APIRouter, Depends, Request, Body
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import AuthServiceDep, get_current_user
from utils.logger import logger
from schemas.login_schemas import UserPostModel, UserGetModel


router = APIRouter(tags=["Login"])


@router.post("/", response_model=None)
async def login_for_access_token(
                                request:Request,
                                auth_service: AuthServiceDep, 
                                form_data: OAuth2PasswordRequestForm = Depends()
                                ):
    user_agent = request.headers.get("user-agent","Unknown Device")
    return await auth_service.user_login_process(user_agent,form_data)

@router.post("/refresh")
async def refresh_access_token(
                               auth_service: AuthServiceDep, 
                               refresh_token: str = Body(..., embed=True)
                               ):
    return await auth_service.update_refresh_token(refresh_token)

@router.post("/register")
async def register_new_user(
                            user_data:UserPostModel, 
                            auth_service: AuthServiceDep
                            ):
    return await auth_service.add_new_user(user_data)

@router.get("/me", response_model = UserGetModel)
async def get_me(current_user: UserGetModel = Depends(get_current_user)):
    return current_user