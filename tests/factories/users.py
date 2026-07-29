from datetime import datetime, timedelta, timezone

from tests.factories.base import BaseFactory
from database.db_model import UserModel, RefreshTokenModel
from core.security import hash_data

RAW_PASSWORD = "Password123_"
PREHASHED_PASSWORD = hash_data("Password123_")

class UserFactory(BaseFactory):
    __model__ = UserModel
    password = PREHASHED_PASSWORD
    
    @classmethod
    def email(cls) -> str:
        return cls.__faker__.safe_email()

class RefreshFactory(BaseFactory):
    __model__ = RefreshTokenModel

    is_used = False
    @classmethod
    def expired_at(cls) -> datetime:
        return datetime.now(timezone.utc) + timedelta(days=14)