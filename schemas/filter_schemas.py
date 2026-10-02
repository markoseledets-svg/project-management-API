from pydantic import BaseModel, Field, ConfigDict, field_validator

from database.db_model import TaskStatus, ProjectStatus, InvitationStatus

class SearchQuery(BaseModel):
    search: str | None = Field(default=None, max_length=100)
    
    model_config = ConfigDict(str_strip_whitespace=True)
    @field_validator('search', mode='before')
    @classmethod
    def sanitize_search(cls, search_query: str) -> str | None:
        if not isinstance(search_query, str):
            return search_query
        clean = search_query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_').strip()
        return clean if clean else None

class TaskFilters(SearchQuery):
    status: TaskStatus | None = None
    has_assignee: bool | None = None

class ProjectFilters(SearchQuery):
    status: ProjectStatus | None = None

class InvitationFilters(BaseModel):
    status:InvitationStatus | None = None
    