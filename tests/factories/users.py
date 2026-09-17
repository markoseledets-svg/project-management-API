from datetime import datetime, timedelta, timezone

from tests.factories.base import BaseFactory
from database.db_model import UserModel, RefreshTokenModel, AuthIdentityModel
from core.security import hash_data

RAW_PASSWORD = "Password123_"
PREHASHED_PASSWORD = hash_data("Password123_")

class UserFactory(BaseFactory):
    __model__ = UserModel
    password = PREHASHED_PASSWORD
    deletes_at = None
    
    @classmethod
    def email(cls) -> str:
        return cls.__faker__.safe_email()

class RefreshFactory(BaseFactory):
    __model__ = RefreshTokenModel

    is_used = False
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    @classmethod
    def expired_at(cls) -> datetime:
        return datetime.now(timezone.utc) + timedelta(days=14)

class AuthIdentityFactory(BaseFactory):
    __model__ = AuthIdentityModel