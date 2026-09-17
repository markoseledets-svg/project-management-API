from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from sqlalchemy import select, update, delete
import uuid6
from datetime import datetime, timezone

from database.db_model import UserModel, RefreshTokenModel, AuthIdentityModel, RegistrationIdentity
from repository.base_repo import BaseRepository
from schemas.login_schemas import RawSessionDataModel, IdentityLoginModel, ProviderResponseModel

class UserRepository(BaseRepository[UserModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(UserModel, session)

    async def get_user_by_email(self, email:str) -> Optional[UserModel]:
        return await self.get_by(email=email)
    
    async def get_user_id_by_email(self,email:str) -> Optional[UserModel]:
        email_obj = await self.session.execute(select(UserModel.public_id).where(UserModel.email == email))
        return email_obj.scalar_one_or_none()
    
    async def get_user_by_id(self,user_id:str) -> Optional[UserModel]:
        return await self.get_by(public_id = user_id)

    async def check_if_user_exists(self, email:str) -> bool:
        user_id = await self.get_columns_by("public_id", email=email)
        return user_id is not None
     
class RefreshRepository(BaseRepository[RefreshTokenModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(RefreshTokenModel, session)
    
    async def get_current_token_record(
                                        self, 
                                        user_public_id:uuid6.UUID,
                                        token_public_id:uuid6.UUID
                                        ) -> RefreshTokenModel|None:
        return await self.get_by(
            user_public_id=user_public_id,
            token_public_id=token_public_id
            )
    
    async def get_token_by_id(
                                    self,
                                    token_public_id:uuid6.UUID
                                    ) -> RefreshTokenModel:
        return await self.get_by(token_public_id=token_public_id)

    async def mark_used_token_by_id(
                                self,
                                token_public_id:uuid6.UUID,
                                ) -> None:
        await self.session.execute(update(RefreshTokenModel)
        .where(RefreshTokenModel.token_public_id == token_public_id)
        .values(is_used=True))
    
    async def invalidate_token_by_family(
                                self,
                                family_id:uuid6.UUID
                                ) -> None:
        await self.session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.family_id == family_id)
            .values(is_used=True)
        )
    async def get_active_tokens_family(self, user_public_id: uuid6.UUID) -> List[uuid6.UUID]:
        family_ids = await self.session.execute(
            select(RefreshTokenModel.family_id)
            .where(
                RefreshTokenModel.user_public_id == user_public_id,
                RefreshTokenModel.is_used == False
                )   
        )
        return family_ids.scalars().all()

    async def invalidate_user_tokens(self, user_public_id: uuid6.UUID) -> None:
        await self.session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.is_used == False, RefreshTokenModel.user_public_id == user_public_id)
            .values(is_used=True)
        )

    async def get_user_active_sessions(self, user_public_id: uuid6.UUID) -> List[RawSessionDataModel]:
        sessions_data_obj = await self.session.execute(select(
                RefreshTokenModel.token_public_id,
                RefreshTokenModel.session_started_at, 
                RefreshTokenModel.user_agent
                )
            .where(
                RefreshTokenModel.user_public_id == user_public_id, 
                RefreshTokenModel.is_used == False,
                RefreshTokenModel.expired_at > datetime.now(timezone.utc)
                )
            )
        return sessions_data_obj.mappings().all()

class AuthIdentityRepository(BaseRepository[AuthIdentityModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(AuthIdentityModel, session)
    
    async def get_identity_by_uid(self, user_public_id: uuid6.UUID, provider:RegistrationIdentity) -> Optional[AuthIdentityModel]:
        return await self.get_by(user_public_id=user_public_id, provider=provider)
    
    async def get_login_data_by_email(self, email: str) -> Optional[IdentityLoginModel]:
        login_data_obj = await self.session.execute(
            select(AuthIdentityModel.user_public_id, AuthIdentityModel.hashed_password, UserModel.deletes_at)
            .join(UserModel, AuthIdentityModel.user_public_id == UserModel.public_id)
            .where(
                AuthIdentityModel.user_relation.has(UserModel.email == email),
                AuthIdentityModel.provider == RegistrationIdentity.LOCAL
            )
        )
        login_data = login_data_obj.mappings().one_or_none()
        if login_data:
            return IdentityLoginModel(
                user_public_id=login_data.user_public_id,
                hashed_password=login_data.hashed_password,
                deletes_at=login_data.deletes_at
            )
        return None

    async def get_identity_with_password(self, user_public_id: uuid6.UUID) -> Optional[AuthIdentityModel]:
        user_identity_obj = await self.session.execute(
            select(AuthIdentityModel)
            .where(AuthIdentityModel.user_public_id == user_public_id,
            AuthIdentityModel.provider == RegistrationIdentity.LOCAL,
            AuthIdentityModel.hashed_password.isnot(None))
        )
        return user_identity_obj.scalar_one_or_none()
    
    async def get_providers_by_email(self, email:str) -> Optional[List[RegistrationIdentity]]:
        user_providers_obj = await self.session.execute(
            select(AuthIdentityModel.provider)
            .where(AuthIdentityModel.user_relation.has(UserModel.email == email))
        )
        providers_lst = []
        for provider in user_providers_obj.scalars().all():
            providers_lst.append(provider)
        return providers_lst

    async def update_user_pwd_by_email(self, email:str, new_hashed_password: str) -> bool:
        result = await self.session.execute(
            update(AuthIdentityModel)
            .where(
                AuthIdentityModel.user_relation.has(UserModel.email == email),
                AuthIdentityModel.provider == RegistrationIdentity.LOCAL
                )
            .values(hashed_password = new_hashed_password)
        )
        return result.rowcount > 0

    async def get_user_id_by_provider_id(self, provider_id:str, identity_provider: RegistrationIdentity) -> uuid6.UUID:
        identity_data = await self.session.execute(
            select(AuthIdentityModel.user_public_id)
            .where(AuthIdentityModel.provider_user_id == provider_id,
            AuthIdentityModel.provider == identity_provider
            )
        )
        return identity_data.scalar_one_or_none()
    
    async def get_providers_by_id(self, user_public_id: uuid6.UUID) -> List[ProviderResponseModel]:
        providers_obj = await self.session.execute(
            select(AuthIdentityModel.identity_public_id, AuthIdentityModel.provider)
            .where(AuthIdentityModel.user_public_id == user_public_id)
        )
        return providers_obj.all()
    
    async def delete_identity_record(
    self, 
    identity_public_id: uuid6.UUID,
    user_public_id: uuid6.UUID
    ) -> bool:
        result = await self.session.execute(
            delete(AuthIdentityModel)
            .where(AuthIdentityModel.identity_public_id == identity_public_id,
            AuthIdentityModel.user_public_id == user_public_id
            )
        )
        return result.rowcount > 0
