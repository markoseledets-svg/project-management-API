from pydantic import BaseModel, Field, model_validator, EmailStr, ConfigDict
import uuid
from datetime import datetime

from database.db_model import ProjectStatus, UserRole

class ProjectBaseModel(BaseModel):
    project_name: str = Field(min_length=1, max_length=255)

    model_config = ConfigDict(str_strip_whitespace=True)

class ProjectPostModel(ProjectBaseModel):
    pass 

class ProjectGetModel(ProjectBaseModel):
    project_public_id: uuid.UUID
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

class ProjectUpdateModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    project_name: str = Field(default=None, min_length=1, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls,data):
        if isinstance(data, dict) and not data:
                raise ValueError("At least one field must be provided for update!")
        return data

class ProjectWithRoleGetModel(ProjectGetModel):
    user_role: UserRole

class PostNewRelation(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    user_role: UserRole

class GetUserDataWithRole(BaseModel):
    email: EmailStr
    user_role: UserRole
    public_id: uuid.UUID

class UpdateUserRole(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_public_id: uuid.UUID
    user_role: UserRole