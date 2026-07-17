from pydantic import BaseModel, model_validator, Field, ConfigDict
import uuid

from database.db_model import UserRole

class BaseTaskModel(BaseModel):
    task_name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=2500)

    model_config = ConfigDict(str_strip_whitespace=True)
class PostTaskModel(BaseTaskModel):
    pass 


class UpdateTaskModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    task_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=2500)
    @model_validator(mode="before")
    @classmethod
    def validate(cls, data):
        if isinstance(data, dict) and not data:
            raise ValueError("At least one field must be provided for update")
        return data
        
class GetTaskModel(BaseTaskModel):
    task_public_id: uuid.UUID
    status: bool
    
    model_config = ConfigDict(from_attributes=True)

