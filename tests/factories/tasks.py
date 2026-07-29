from tests.factories.base import BaseFactory
from database.db_model import TaskModel

class TaskFactory(BaseFactory):
    __model__ = TaskModel