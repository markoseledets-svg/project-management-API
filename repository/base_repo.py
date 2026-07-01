from typing import Generic, TypeVar, Type, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.db_model import Base
ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    def add(self, obj: ModelType) -> None:
        self.session.add(obj)
    
    def update(self, db_obj:ModelType, update_data: dict) -> ModelType:
        for key, value in update_data.items():
            if hasattr(db_obj,key):
                setattr(db_obj, key, value)
        return db_obj
    
    async def get_by(self, **kwargs: Any) -> Optional[ModelType]:
        query = await self.session.execute(select(self.model).filter_by(**kwargs))
        result = query.scalar_one_or_none()
        return result
    
    async def get_columns_by(self, *args:Any, **kwargs: Any) -> Optional[ModelType]:
        selected_columns = [getattr(self.model,arg) for arg in args]
        query = await self.session.execute(select(*selected_columns).filter_by(**kwargs))
        return query.mappings().one_or_none()
    
    async def delete(self, db_obj:ModelType) -> None:
        await self.session.delete(db_obj)