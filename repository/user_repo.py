from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from sqlalchemy import select, update
import uuid6

from database.db_model import UserModel, RefreshTokenModel
from repository.base_repo import BaseRepository

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
    
    async def check_if_token_exists(
                                    self,
                                    token_public_id:uuid6.UUID
                                    ) -> bool:
        token_id = await self.get_columns_by("token_public_id", token_public_id=token_public_id)
        return token_id is not None

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
 