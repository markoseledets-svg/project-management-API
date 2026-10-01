from enum import Enum

class SortOrder(str, Enum):
    ASC='asc'
    DESC='desc'

class ProjectSortField(str, Enum):
    CREATED_AT = 'created_at'
    UPDATED_AT = 'updated_at'
    PROJECT_NAME = 'project_name'

class TaskSortField(str, Enum):
    CREATED_AT = 'created_at'
    TASK_NAME = 'task_name'
    