from schemas.login_schemas import UserGetModel
import uuid6
import time
from random import randint
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from datetime import datetime, timedelta, timezone
import json

from services.redis_services import RedisServices
from repository.user_repo import UserRepository,RefreshRepository, AuthIdentityRepository
from schemas.login_schemas import (
    UserWithOtp, 
    UserRegisterModel, 
    TokenResponseModel, 
    SessionsGetModel, 
    ChangePasswordModel,
    UserAuthModel,
    IdentityLoginModel,
    ProviderResponseModel
    )
from database.db_model import UserModel, RefreshTokenModel, AuthIdentityModel, RegistrationIdentity
from core.security import (
    hash_data, 
    verify_hashes, 
    generate_refresh_token_data,
    generate_refresh_jwt, 
    generate_access_jwt, 
    decode_refresh_token, 
    decode_access_token,
    generate_restore_jwt,
    decode_restore_token
    )
from utils.logger import logger
from utils.user_agent_parser import parse_user_agent
from core.exceptions import (
    ConflictError, 
    AuthFailedError, 
    NotFoundError, 
    DataValidationError,
    ForbiddenError
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
        self.auth_identity_repo = AuthIdentityRepository(session)
        self.redis_client = RedisServices(client)

    async def set_email_verification_data(
        self,
        redis_key: str,
        values_dict: dict,
        password: str
        ) -> int:
        hashed_password = hash_data(password)
        values_dict['password']=hashed_password
        otp=randint(100000, 999999)
        values_dict['otp']=otp
        await self.redis_client.add_user_otp(redis_key,values_dict)
        return otp

    async def get_email_verification_data(self, redis_key:str, otp:int) -> dict:
        user_json_data = await self.redis_client.get_user_otp_data(
            redis_key
        )
        user_data = json.loads(user_json_data)
        if user_data['otp'] != otp:
            raise AuthFailedError()
        await self.redis_client.delete_otp_data(redis_key)
        return user_data

    async def start_user_registration(
                                        self,
                                        user_data: UserRegisterModel,
                                    ) -> int:
        user_exists = await self.user_repo.check_if_user_exists(user_data.email)
        if user_exists:
            raise ConflictError(detail="User with this email already exists!")
        return await self.set_email_verification_data(
            f'register:{user_data.email}',
            {'email':user_data.email},
            user_data.password.get_secret_value()
        )

    def _register_user(self, email:str) -> UserModel:
        return self.user_repo.create(
            public_id = uuid6.uuid7(),
            email=email
        )
        

    def _add_identity(
        self, 
        user_public_id:uuid6.UUID, 
        provider: RegistrationIdentity,
        openid:str | None = None,
        hashed_password: str | None = None
        ) -> AuthIdentityModel:
        return self.auth_identity_repo.create(
            identity_public_id=uuid6.uuid7(),
            user_public_id=user_public_id,
            provider=provider,
            hashed_password=hashed_password,
            provider_user_id=openid
        )

    async def verify_user_registration(self, email:str, otp: str) -> None:
        user_otp_data = await self.get_email_verification_data(f'register:{email}', otp)
        user_data = UserWithOtp.model_validate(user_otp_data)
        new_user = self._register_user(email)
        self._add_identity(
            user_public_id=new_user.public_id,
            hashed_password=user_data.password.get_secret_value(),
            provider=RegistrationIdentity.LOCAL
        )
        try:    
            await self.session.commit()
            logger.info(f"New user with public id:{new_user.public_id} was succesfully added to db!")
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(detail="User with this email already exists!")
    
    async def verify_user_login(self,data:UserAuthModel) -> Optional[IdentityLoginModel]:
        login_data = await self.auth_identity_repo.get_login_data_by_email(data.email)
        if not login_data:
            raise AuthFailedError()
        if not verify_hashes(data.password.get_secret_value(), login_data.hashed_password.get_secret_value()):
            logger.warning(f"Unsuccesfull attempt to login to email {data.email}!")
            raise AuthFailedError()
        return login_data
    
    async def get_user_by_public_id(self,user_public_id:uuid6.UUID) -> Optional[UserModel]:
        user = await self.user_repo.get_user_by_id(user_public_id)
        if not user:
            raise NotFoundError()
        return user
    
    async def add_token_record(
        self, 
        user_public_id:uuid6.UUID, 
        useragent:str,
        family_id: Optional[uuid6.UUID] = None
        ) -> RefreshTokenModel:
        new_refresh_token_data = generate_refresh_token_data(user_public_id,useragent, family_id)
        new_refresh_token = self.refresh_repo.create(**new_refresh_token_data)
        await self.session.commit()
        return new_refresh_token

    def _generate_auth_tokens(
        self,
        user_public_id:uuid6.UUID, 
        token_family: uuid6.UUID, 
        refresh_token_public_id: uuid6.UUID
        ) -> TokenResponseModel:
        access_token = generate_access_jwt(
            user_public_id,
            token_family
        )
        refresh_token = generate_refresh_jwt(
            user_public_id,
            refresh_token_public_id
        )
        return TokenResponseModel(
            is_restore=False,
            access_token=access_token,
            refresh_token=refresh_token
        )

    async def _get_tokens_on_login(
        self, 
        user_agent:str,
        user_public_id: uuid6.UUID,
        deletes_at: datetime|None=None,
        ) -> TokenResponseModel:
        if deletes_at:
            restore_token = generate_restore_jwt(user_public_id)
            return TokenResponseModel(
                is_restore=True,
                restore_token=restore_token,
                deletes_at=deletes_at
            )
        token_record = await self.add_token_record(user_public_id, user_agent)
        return self._generate_auth_tokens(
            user_public_id,
            token_record.family_id,
            token_record.token_public_id
        )

    async def user_login_process(self, 
                                 user_agent:str, 
                                 form_data:OAuth2PasswordRequestForm
                                 ) -> TokenResponseModel:
            try:
                user_data = UserAuthModel(email=form_data.username, password=form_data.password)
            except ValidationError:
                raise DataValidationError()
            login_data = await self.verify_user_login(user_data)
            return await self._get_tokens_on_login(
                user_agent,
                login_data.user_public_id,
                login_data.deletes_at
                )

    async def rotate_refresh_token(self, user_refresh_token:str, user_agent:str) -> TokenResponseModel:
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
                return TokenResponseModel(**is_retry_token_data)
            await self.refresh_repo.invalidate_token_by_family(token_record.family_id)
            await self.session.commit()
            raise AuthFailedError()
        token_record.is_used = True
        await self.session.flush()
        user = await self.get_user_by_public_id(user_public_id)
        if not user:
            raise AuthFailedError()
        refresh_token_record = await self.add_token_record(
                                                            user.public_id, 
                                                            user_agent, 
                                                            token_record.family_id
                                                         )
        tokens = self._generate_auth_tokens(
                    user.public_id,
                    refresh_token_record.family_id,
                    refresh_token_record.token_public_id
                )
        await self.redis_client.save_token_data_for_retries(user_refresh_token, tokens)
        return tokens
    
    async def get_user_credentials(self, token:str, user_data: dict|None = None) -> UserGetModel:
        is_banned = await self.redis_client.check_banned_tokens(token)
        if is_banned:
            raise AuthFailedError()
        if not user_data:
            user_data = decode_access_token(token)
        is_family_banned = await self.redis_client.check_banned_tokens(user_data['token_family_id'])
        if is_family_banned:
            raise AuthFailedError()
        user = await self.user_repo.get_user_by_id(user_data["user_public_id"])
        if not user:
            raise AuthFailedError()
        return user
    
    def _validate_user_tokens(self, access_token: str, refresh_token: str) -> List:
        if not access_token or not refresh_token:
            raise AuthFailedError()
        access_token_data = decode_access_token(access_token)
        refresh_token_data =  decode_refresh_token(refresh_token)
        if access_token_data["user_public_id"] != refresh_token_data["user_public_id"]:
            raise AuthFailedError()
        return [access_token_data, refresh_token_data]

    async def user_logout_process(
                                    self,
                                    user_access_token:str,
                                    user_refresh_token:str
                                    ) -> None:
        token_data_lst = self._validate_user_tokens(user_access_token, user_refresh_token)
        token_exp = token_data_lst[0]["token_expiration"]
        refresh_token_id = token_data_lst[1]["token_public_id"]
        token_record = await self.refresh_repo.get_token_by_id(refresh_token_id)
        if not token_record or token_record.is_used:
            raise AuthFailedError()
        token_record.is_used = True
        await self.redis_client.save_banned_access_token(user_access_token, token_exp)
        await self.refresh_repo.mark_used_token_by_id(refresh_token_id)
        await self.session.commit()

    async def get_user_active_sessions(self, user_public_id: uuid6.UUID) -> List[SessionsGetModel]:
        user_session_lst = await self.refresh_repo.get_user_active_sessions(
            user_public_id
        )
        parsed_sessions_lst = []
        for user_session in user_session_lst:
            parsed_user_agent_data = parse_user_agent(user_session['user_agent'])
            session = SessionsGetModel(
                token_public_id=user_session['token_public_id'],
                session_started_at=user_session['session_started_at'],
                **parsed_user_agent_data
            )
            parsed_sessions_lst.append(session)
        return parsed_sessions_lst

    async def logout_everywhere(
        self,
        user_access_token: str,
        user_refresh_token: str
        ) -> None:
        token_data_lst = self._validate_user_tokens(user_access_token, user_refresh_token)
        user_public_id = token_data_lst[0]['user_public_id']
        family_ids = await self.refresh_repo.get_active_tokens_family(user_public_id)
        await self.refresh_repo.invalidate_user_tokens(user_public_id)
        for family_id in family_ids:
            await self.redis_client.save_banned_access_token(family_id, time.time() + 900)
        await self.session.commit()

    async def logout_session(self, user_public_id: uuid6.UUID, token_public_id: uuid6.UUID) -> None:
        token_record = await self.refresh_repo.get_current_token_record(user_public_id, token_public_id)
        if not token_record or token_record.is_used == True:
            raise NotFoundError()
        token_record.is_used = True
        await self.redis_client.save_banned_access_token(token_record.family_id, time.time() + 900)
        await self.session.commit()

    async def delete_user_account(
        self,
        access_token: str,
        refresh_token: str
        ) -> None:
        token_data_lst = self._validate_user_tokens(access_token, refresh_token)
        user = await self.get_user_by_public_id(token_data_lst[0]['user_public_id'])
        if not user:
            raise AuthFailedError()
        user.deletes_at = datetime.now(timezone.utc) + timedelta(days=14)
        await self.logout_everywhere(access_token, refresh_token)

    async def verify_user_restore(self, restore_token: str) -> None:
        is_banned = await self.redis_client.check_banned_tokens(restore_token)
        if is_banned:
            raise AuthFailedError()
        user_public_id = decode_restore_token(restore_token)
        user = await self.get_user_by_public_id(user_public_id)
        if not user:
            raise AuthFailedError()
        user.deletes_at = None
        await self.redis_client.save_banned_access_token(restore_token, time.time() + 600)
        await self.session.commit()

    async def _invalidate_user_sessions(self, user_public_id: uuid6.UUID) -> None:
        family_ids = await self.refresh_repo.get_active_tokens_family(user_public_id)
        if family_ids:
            await self.refresh_repo.invalidate_user_tokens(user_public_id)
            for family_id in family_ids:
                await self.redis_client.save_banned_access_token(family_id, time.time() + 900)

    async def change_password(
        self,
        user: UserModel,
        user_data: ChangePasswordModel
        ) -> None:
        user_identity = await self.auth_identity_repo.get_identity_with_password(user.public_id)
        if not user_identity:
            raise AuthFailedError(detail="You can't change password, because your account was created with google.")
        if not verify_hashes(user_data.old_password.get_secret_value(), user_identity.hashed_password):
            raise AuthFailedError()
        user_identity.hashed_password = hash_data(user_data.password.get_secret_value())
        await self._invalidate_user_sessions(user.public_id)
        await self.session.commit()

    async def change_forgotten_password(
        self,
        user_data: UserRegisterModel
        ) -> int:
        providers = await self.auth_identity_repo.get_providers_by_email(user_data.email)
        if not providers or RegistrationIdentity.LOCAL not in providers:
            raise AuthFailedError()
        return await self.set_email_verification_data(
            f'password-change:{user_data.email}',
            {'email':user_data.email},
            user_data.password.get_secret_value()
        )

    async def verify_pwd_change_with_otp(
        self,
        otp: int,
        email: str
        ) -> None:
        user_otp_data = await self.get_email_verification_data(f'password-change:{email}', otp)
        user_data = UserWithOtp.model_validate(user_otp_data)
        updated = await self.auth_identity_repo.update_user_pwd_by_email(
            email, 
            user_data.password.get_secret_value()
            )
        if not updated:
            raise AuthFailedError()
        uid = await self.user_repo.get_user_id_by_email(email)
        await self._invalidate_user_sessions(uid)
        await self.session.commit()

    async def auth_with_provider(
        self, 
        email: str, 
        provider_id:str, 
        user_agent: str,
        auth_provider: RegistrationIdentity
        ) -> TokenResponseModel:
        user_public_id = await self.auth_identity_repo.get_user_id_by_provider_id(
            provider_id,
            auth_provider
        )
        if user_public_id:
            user = await self.user_repo.get_user_by_id(user_public_id)
        else:
            user = await self.user_repo.get_user_by_email(email)
            if not user:
                user = self._register_user(email)
            self._add_identity(
                    user_public_id=user.public_id, 
                    openid=provider_id, 
                    provider=auth_provider
                    )
        if user.deletes_at is not None:
            await self.session.commit()
        return await self._get_tokens_on_login(
            user_agent,
            user.public_id,
            user.deletes_at
        )
    
    async def link_provider(self, user:UserModel, provider_id: str, provider: RegistrationIdentity) -> None:
        identity= await self.auth_identity_repo.get_identity_by_uid(user.public_id, provider)
        if identity:
            raise ConflictError(detail='Provider already linked.')
        self._add_identity(
            user_public_id=user.public_id,
            openid= provider_id,
            provider=provider
        )
        await self.session.commit()

    def _get_email(self, form_data:List[dict]) -> str:
        user_email = next((user_data['email'] for user_data in form_data 
            if user_data.get('primary')==True and user_data.get('verified')==True), None)
        if user_email:
           return user_email
        user_email = next((user_data['email'] for user_data in form_data 
            if user_data.get('verified')==True), None)
        if user_email:
            return user_email
        raise AuthFailedError(detail='No verified email address associated with this GitHub account')
        
    async def auth_with_github(self, email_data: List[dict], uid:str, user_agent: str) -> TokenResponseModel:
        user_email = self._get_email(email_data)
        return await self.auth_with_provider(
            user_email,
            uid, 
            user_agent, 
            RegistrationIdentity.GITHUB
        )

    async def auth_with_google(self, form_data: dict, user_agent: str) -> TokenResponseModel:
        return await self.auth_with_provider(
            form_data.get('email'),
            form_data.get('sub'),
            user_agent,
            RegistrationIdentity.GOOGLE
        )
    
    async def link_github(self, user: UserModel, user_data: dict) -> None:
        return await self.link_provider(
            user,
            str(user_data.get('id')),
            RegistrationIdentity.GITHUB
        )

    async def link_google(self, user:UserModel, form_data: dict) -> None:
        return await self.link_provider(
            user,
            form_data.get('sub'),
            RegistrationIdentity.GOOGLE
        )

    async def add_password(self, user: UserGetModel, password: str) -> int:
        identity = await self.auth_identity_repo.get_identity_by_uid(user.public_id, RegistrationIdentity.LOCAL)
        if identity:
            raise ForbiddenError()
        return await self.set_email_verification_data(
            f'add-password:{user.public_id}',
            {},
            password
        )
    
    async def confirm_password_adding_with_otp(self, user_public_id: uuid6.UUID, otp:int) -> None:
        user_data = await self.get_email_verification_data(f'add-password:{user_public_id}', otp)
        self._add_identity(
            user_public_id=user_public_id,
            provider=RegistrationIdentity.LOCAL,
            hashed_password=user_data['password']
        )
        await self.session.commit()

    async def get_users_auth_providers(self, user: UserGetModel) -> List[ProviderResponseModel]:
        return await self.auth_identity_repo.get_providers_by_id(user.public_id)
    
    async def unlink_identity(
        self, 
        user: UserGetModel, 
        identity_public_id: uuid6.UUID 
        ) -> None:
        providers = await self.auth_identity_repo.get_providers_by_id(user.public_id)
        is_local = any(identity_id == identity_public_id and provider == RegistrationIdentity.LOCAL
                        for identity_id, provider in providers)
        if len(providers) == 1 or is_local:
            raise ForbiddenError()
        is_deleted = await self.auth_identity_repo.delete_identity_record(
            identity_public_id,
            user.public_id
        ) 
        if not is_deleted:
            raise NotFoundError()
        await self.session.commit()
