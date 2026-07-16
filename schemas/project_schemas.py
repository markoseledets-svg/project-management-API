from pydantic import BaseModel, Field, model_validator, EmailStr
import uuid
from datetime import datetime

from database.db_model import ProjectStatus, UserRole

class ProjectBaseModel(BaseModel):
    project_name: str = Field(min_length=3, max_length=150)

class ProjectPostModel(ProjectBaseModel):
    pass 

class ProjectGetModel(ProjectBaseModel):
    project_public_id: uuid.UUID
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

class ProjectUpdateModel(BaseModel):
    project_name: str = Field(default=None, min_length=3, max_length=150)

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls,data):
        if isinstance(data, dict) and not data:
                raise ValueError("At least one field must be provided for update")
        return data
class ProjectWithRoleGetModel(ProjectGetModel):
    user_role: UserRole

class PostNewRelation(BaseModel):
    email: EmailStr
    user_role: UserRole

class GetUserDataWithRole(PostNewRelation):
    public_id: uuid.UUID

class UpdateUserRole(BaseModel):
    user_public_id: uuid.UUID
    user_role: UserRole