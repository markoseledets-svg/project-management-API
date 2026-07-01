from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from sqlalchemy import select
import uuid

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
    
class RefreshRepository(BaseRepository[RefreshTokenModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(RefreshTokenModel, session)
    
    async def get_current_token_reccord(
                                        self, 
                                        user_public_id:uuid.UUID,
                                        token_public_id:uuid.UUID
                                        ) -> RefreshTokenModel|None:
        return await self.get_by(
            user_public_id=user_public_id,
            token_public_id=token_public_id
            )
    
    

    
    