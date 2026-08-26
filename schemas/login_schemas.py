from pydantic import (
        BaseModel, 
        EmailStr, 
        Field, 
        ConfigDict,
        field_validator,
        SecretStr,
        )
import uuid
import re
from datetime import datetime

from core.exceptions import DataValidationError

class UserBaseModel(BaseModel):
    email: EmailStr
     
    model_config = ConfigDict(str_strip_whitespace=True)
    

class UserGetModel(UserBaseModel):
    public_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)

class UserPostModel(UserBaseModel):
    password: SecretStr = Field(min_length=8, max_length=64)

_PASSWORD_PATTERN = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[\W_]).+$"

def _validate_strong_password(v: SecretStr) -> SecretStr:
    if not re.match(_PASSWORD_PATTERN, v.get_secret_value()):
        raise ValueError(
            "Password must contain at least one uppercase letter, "
            "one number and one special character!"
        )
    return v

class UserRegisterModel(UserPostModel):
    @field_validator("password", mode="after")
    def validate_password(cls, v: SecretStr) -> SecretStr:
        return _validate_strong_password(v)

class ChangePasswordModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    old_password: SecretStr = Field(min_length=8, max_length=64)
    password: SecretStr = Field(min_length=8, max_length=64)

    @field_validator("password", mode="after")
    def validate_password(cls, v: SecretStr) -> SecretStr:
        return _validate_strong_password(v)

class UserWithOtp(UserPostModel):
    otp: int = Field(ge=100000, le=999999)

class VerifyOTPModel(UserBaseModel):
    otp: int = Field(ge=100000, le=999999)

class TokenResponseModel(BaseModel):
    is_restore: bool
    refresh_token: str | None = None
    access_token: str | None = None
    restore_token: str | None = None
    deletes_at: datetime | None = None

class RawSessionDataModel(BaseModel):
    token_public_id: uuid.UUID
    session_started_at: datetime
    user_agent: str

class SessionsGetModel(BaseModel):
    token_public_id: uuid.UUID
    session_started_at: datetime
    device_type: str
    browser_data: str | None = None
    os_data: str | None = None
    device_model: str | None = None
