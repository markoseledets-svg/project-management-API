from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # Database
    database_url: str
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_db: str | None = None

    # Database Pool
    pool_size: int = 15
    max_overflow: int = 15
    pool_timeout: int = 30

    # Security / Auth
    access_secret_key: str
    refresh_secret_key: str
    restore_secret_key: str
    session_secret_key: str
    algorithm: str = "HS256"

    # Environment
    env: str = "production"

    # Test Database
    test_database_url: str
    bench_database_url: str | None = None
    postgres_test_db: str | None = None
    postgres_test_user: str | None = None
    postgres_test_password: str | None = None

    # CORS
    cors_origins: List[str] = ["http://localhost", "http://localhost:8000"]

    # Redis
    redis_password: str | None = None
    redis_url: str
    redis_max_connections: int = 100

    # Email / SMTP
    smtp_key: str
    smtp_login: str
    email_sender: str | None = None
    smtp_port: int = 587
    smtp_server: str

    # OAuth
    google_client_id: str
    google_client_secret: str
    github_client_id: str
    github_client_secret: str

    # Feature flags
    enable_caching: bool = True
    enable_global_rate_limit: bool = True

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.env.lower() == "development"

settings = Settings()

