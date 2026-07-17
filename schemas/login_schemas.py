from pydantic import (
        BaseModel, 
        EmailStr, 
        Field, 
        ConfigDict,
        field_validator,
        SecretStr
        )
import uuid
import re

from core.exceptions import DataValidationError

class UserBaseModel(BaseModel):
    email: EmailStr
     
    model_config = ConfigDict(str_strip_whitespace=True)
    

class UserGetModel(UserBaseModel):
    public_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)

class UserPostModel(UserBaseModel):
    password: SecretStr = Field(min_length=8, max_length=64)

class UserRegisterModel(UserPostModel):
    @field_validator("password", mode="after")
    def validate_password(cls, v:SecretStr) -> SecretStr:
        password_raw = v.get_secret_value()
        pattern = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[\W_]).+$"
        if not re.match(pattern, password_raw):
            raise ValueError(
                """Password should contain at least one uppercase letter, 
                one number and one special character!"""
            )
        return v

class UserWithOtp(UserPostModel):
    otp: int = Field(ge=100000, le=999999)

class VerifyOTPModel(UserBaseModel):
    otp: int = Field(ge=100000, le=999999)