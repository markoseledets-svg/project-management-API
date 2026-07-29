from tests.factories.base import BaseFactory
from database.db_model import ProjectModel, UserProjectRelation

class ProjectFactory(BaseFactory):
    __model__ = ProjectModel

class UserProjectFactory(BaseFactory):
    __model__ = UserProjectRelation
