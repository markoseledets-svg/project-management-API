from pydantic import BaseModel, model_validator
import uuid

from database.db_model import UserRole

class BaseTaskModel(BaseModel):
    task_name: str
    description: str | None = None

class PostTaskModel(BaseTaskModel):
    pass 


class UpdateTaskModel(BaseModel):
    task_name: str | None = None
    description: str | None = None
    @model_validator(mode="before")
    @classmethod
    def validate(cls, data):
        if isinstance(data, dict) and not data:
            raise ValueError("At least one field must be provided for update")
        return data
        
class GetTaskModel(BaseTaskModel):
    task_public_id: uuid.UUID
    status: bool
    
    model_config = {"from_attributes": True}

