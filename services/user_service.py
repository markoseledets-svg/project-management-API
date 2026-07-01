import uuid6
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from typing import Optional
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError

from repository.user_repo import UserRepository,RefreshRepository
from schemas.login_schemas import UserPostModel
from database.db_model import UserModel, RefreshTokenModel
from core.security import (
    hash_data, 
    verify_hashes, 
    generate_refresh_token_data,
    generate_refresh_token, 
    generate_access_token, 
    decode_refresh_token, 
    decode_access_token
    )
from utils.logger import logger
from core.exceptions import (
    UserAlreadyExistsError, 
    AuthFailedError, NotFoundError, 
    DataValidationError, 
    TokenError
)


class AuthServices:
    def __init__(
                self, 
                 session:AsyncSession,
                 ):
        self.session = session
        self.user_repo = UserRepository(session)
        self.refresh_repo = RefreshRepository(session)
        
    async def add_new_user(self,user_post_data:UserPostModel) -> None:
        hashed_password = hash_data(user_post_data.password)
        public_user_id = uuid6.uuid7()
        
        new_user = UserModel(
            public_id = public_user_id,
            email = user_post_data.email,
            password = hashed_password,
        )
        self.user_repo.add(new_user)
        try:    
            await self.session.commit()
            logger.info(f"New user with public id:{public_user_id} was succesfully added to db!")
        except IntegrityError:
            await self.session.rollback()
            raise UserAlreadyExistsError()
    
    async def verify_user_login(self,data:UserPostModel) -> Optional[UserModel]:
        user = await self.user_repo.get_user_by_email(data.email)
        if not user:
            raise AuthFailedError()
        if not verify_hashes(data.password, user.password):
            logger.warning(f"Unsuccesfull attempt to login to email {data.email}!")
            raise AuthFailedError()
        return user
    
    async def get_user_by_public_id(self,user_public_id:uuid6.UUID) -> Optional[UserModel]:
        user = await self.user_repo.get_user_by_id(user_public_id)
        if not user:
            raise NotFoundError()
        return user
    
    async def generate_jwt_token(self, user_public_id:uuid6.UUID, useragent:str) -> RefreshTokenModel:
        new_refresh_token_data = generate_refresh_token_data(user_public_id,useragent)
        new_refresh_token = RefreshTokenModel(**new_refresh_token_data)
        self.refresh_repo.add(new_refresh_token)
        await self.session.commit()
        await self.session.refresh(new_refresh_token)
        token_public_id = new_refresh_token.token_public_id
        return generate_refresh_token(user_public_id, token_public_id)
    
    async def user_login_process(self, 
                                 user_agent:str, 
                                 form_data:OAuth2PasswordRequestForm
                                 ) -> Optional[dict]:
            try:
                user_data = UserPostModel(email=form_data.username, password=form_data.password)
            except ValidationError:
                raise DataValidationError()
            user = await self.verify_user_login(user_data)
            access_token = generate_access_token(user.public_id)
            refresh_token = await self.generate_jwt_token(user.public_id,user_agent)
            return {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer"
                    }

    async def update_refresh_token(self, user_refresh_token:str) -> dict:
        decoded_token = decode_refresh_token(user_refresh_token)
        user_public_id = decoded_token["user_public_id"]
        token_public_id = decoded_token["token_public_id"]
        token_record = await self.refresh_repo.get_current_token_reccord(
            user_public_id,
            token_public_id
        )
        if not token_record:
            raise AuthFailedError()
        user_agent = token_record.user_agent
        await self.session.delete(token_record)
        await self.session.flush()
        user = await self.get_user_by_public_id(user_public_id)
        if not user:
            raise AuthFailedError()
        access_token = generate_access_token(user.public_id)
        refresh_token = await self.generate_jwt_token(user.public_id, user_agent)
        return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer"
                }
    
    async def get_user_credentials(self,token:str):
        user_public_id = decode_access_token(token)
        user = await self.user_repo.get_user_by_id(user_public_id)
        if not user:
            raise TokenError()
        return user
    