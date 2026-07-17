import uuid6
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from typing import Optional
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError

from services.redis_services import RedisServices
from repository.user_repo import UserRepository,RefreshRepository
from schemas.login_schemas import UserPostModel, UserWithOtp, UserRegisterModel
from database.db_model import UserModel, RefreshTokenModel
from core.security import ( 
    verify_hashes, 
    generate_refresh_token_data,
    generate_refresh_jwt, 
    generate_access_jwt, 
    decode_refresh_token, 
    decode_access_token
    )
from utils.logger import logger
from core.exceptions import (
    ConflictError, 
    AuthFailedError, 
    NotFoundError, 
    DataValidationError
)


class AuthServices:
    def __init__(
                self, 
                session:AsyncSession,
                client:redis.Redis
                ):
        self.session = session
        self.user_repo = UserRepository(session)
        self.refresh_repo = RefreshRepository(session)
        self.redis_client = RedisServices(client)

    async def start_user_registration(
                                        self,
                                        user_data: UserRegisterModel,
                                    ) -> int:
        user_exists = await self.user_repo.check_if_user_exists(user_data.email)
        if user_exists:
            raise ConflictError(detail="User with this email already exists!")
        return await self.redis_client.add_user_otp(user_data)

    async def verify_user_registration(self, email:str, otp: str) -> None:
        user_json_data = await self.redis_client.get_user_registration_data(email)
        user_data = UserWithOtp.model_validate_json(user_json_data)
        if otp != user_data.otp:
            raise AuthFailedError()
        await self.redis_client.delete_otp_data(email)
        public_user_id = uuid6.uuid7()
        new_user = UserModel(
            public_id = public_user_id,
            email = email,
            password = user_data.password.get_secret_value(),
        )
        self.user_repo.add(new_user)
        try:    
            await self.session.commit()
            logger.info(f"New user with public id:{public_user_id} was succesfully added to db!")
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(detail="User with this email already exists!")
    
    async def verify_user_login(self,data:UserPostModel) -> Optional[UserModel]:
        user = await self.user_repo.get_user_by_email(data.email)
        if not user:
            raise AuthFailedError()
        if not verify_hashes(data.password.get_secret_value(), user.password):
            logger.warning(f"Unsuccesfull attempt to login to email {data.email}!")
            raise AuthFailedError()
        return user
    
    async def get_user_by_public_id(self,user_public_id:uuid6.UUID) -> Optional[UserModel]:
        user = await self.user_repo.get_user_by_id(user_public_id)
        if not user:
            raise NotFoundError()
        return user
    
    async def generate_refresh_token(
        self, 
        user_public_id:uuid6.UUID, 
        useragent:str,
        family_id: Optional[uuid6.UUID] = None
        ) -> str:
        new_refresh_token_data = generate_refresh_token_data(user_public_id,useragent, family_id)
        new_refresh_token = RefreshTokenModel(**new_refresh_token_data)
        self.refresh_repo.add(new_refresh_token)
        await self.session.commit()
        await self.session.refresh(new_refresh_token)
        token_public_id = new_refresh_token.token_public_id
        return generate_refresh_jwt(user_public_id, token_public_id)

    async def user_login_process(self, 
                                 user_agent:str, 
                                 form_data:OAuth2PasswordRequestForm
                                 ) -> Optional[dict]:
            try:
                user_data = UserPostModel(email=form_data.username, password=form_data.password)
            except ValidationError:
                raise DataValidationError()
            user = await self.verify_user_login(user_data)
            access_token = generate_access_jwt(user.public_id)
            refresh_token = await self.generate_refresh_token(user.public_id,user_agent)
            return {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    }

    async def rotate_refresh_token(self, user_refresh_token:str, user_agent:str) -> dict:
        if not user_refresh_token:
            raise AuthFailedError()
        decoded_token = decode_refresh_token(user_refresh_token)
        user_public_id = decoded_token["user_public_id"]
        token_public_id = decoded_token["token_public_id"]
        token_record = await self.refresh_repo.get_current_token_record(
            user_public_id,
            token_public_id
        )
        if not token_record:
            raise AuthFailedError()
        if token_record.is_used == True:
            is_retry_token_data = await self.redis_client.check_refresh_for_retries(user_refresh_token)
            if is_retry_token_data:
                return is_retry_token_data
            await self.refresh_repo.invalidate_token_by_family(token_record.family_id)
            await self.session.commit()
            raise AuthFailedError()
        token_record.is_used = True
        await self.session.flush()
        user = await self.get_user_by_public_id(user_public_id)
        if not user:
            raise AuthFailedError()
        access_token = generate_access_jwt(user.public_id)
        refresh_token = await self.generate_refresh_token(
                                                            user.public_id, 
                                                            user_agent, 
                                                            token_record.family_id
                                                         )
        tokens_data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                }
        await self.redis_client.save_token_data_for_retries(user_refresh_token, tokens_data)
        return tokens_data
    
    async def get_user_credentials(self, token:str):
        is_banned = await self.redis_client.check_banned_tokens(token)
        if is_banned:
            raise AuthFailedError()
        user_data = decode_access_token(token)
        user = await self.user_repo.get_user_by_id(user_data["user_public_id"])
        if not user:
            raise AuthFailedError()
        return user
    
    async def user_logout_process(
                                    self,
                                    user_access_token:str,
                                    user_refresh_token:str
                                    ) -> None:
        if not user_access_token or not user_refresh_token:
            raise AuthFailedError()
        access_token_data = decode_access_token(user_access_token)
        refresh_token_data =  decode_refresh_token(user_refresh_token)
        access_user_public_id = access_token_data["user_public_id"]
        refresh_user_public_id = refresh_token_data["user_public_id"]
        refresh_token_id = refresh_token_data["token_public_id"]
        if access_user_public_id != refresh_user_public_id:
            raise AuthFailedError()
        token_exp = access_token_data["token_exparation"]
        token_record = await self.refresh_repo.get_token_by_id(refresh_token_id)
        if not token_record or token_record.is_used:
            raise AuthFailedError()
        await self.redis_client.save_banned_access_token(user_access_token, token_exp)
        await self.refresh_repo.mark_used_token_by_id(refresh_token_id)
        await self.session.commit()
