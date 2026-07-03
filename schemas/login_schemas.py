from pydantic import BaseModel, EmailStr, Field
import uuid

class UserBaseModel(BaseModel):
    email: EmailStr
    

class UserGetModel(UserBaseModel):
    public_id: uuid.UUID

    model_config = {"from_attributes": True}

class UserPostModel(UserBaseModel):
    password: str = Field(min_length=8, max_length=64)

class UserWithOtp(UserPostModel):
    otp: int = Field(ge=100000, le=999999)

class VerifyOTPModel(UserBaseModel):
    otp: int = Field(ge=100000, le=999999)