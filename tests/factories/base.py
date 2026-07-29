from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory
from sqlalchemy.ext.asyncio import AsyncSession

class BaseFactory(SQLAlchemyFactory):
    __is_base_factory__ = True
    __set_relationships__ = False