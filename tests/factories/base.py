from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

class BaseFactory(SQLAlchemyFactory):
    __is_base_factory__ = True
    __set_relationships__ = False