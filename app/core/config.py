from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # =========================
    # App Settings
    # =========================
    APP_NAME: str = "Backend"
    ENV: str = Field(default="development")
    DEBUG: bool = False

    # =========================
    # Database Settings
    # =========================
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "auth_db"

    # =========================
    # JWT Settings
    # =========================
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # =========================
    # Pydantic Config
    # =========================
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # =========================
    # Validators
    # =========================
    @field_validator("ENV")
    @classmethod
    def validate_env(cls, v: str):
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENV must be one of {allowed}")
        return v

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str):
        if len(v) < 16:
            raise ValueError("JWT_SECRET must be at least 16 characters long")
        return v

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES", "REFRESH_TOKEN_EXPIRE_DAYS")
    @classmethod
    def validate_positive(cls, v: int):
        if v <= 0:
            raise ValueError("Token expiry values must be positive")
        return v

    # =========================
    # Computed Properties
    # =========================
    @property
    def database_url(self) -> str:
        """Sync DB URL (useful for Alembic)"""  
        # postgresql://user:pass@host:port/db
        return (
            f"postgresql://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )

    @property
    def async_database_url(self) -> str:
        """Async DB URL (for FastAPI runtime)"""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )


# =========================
# Cached Settings Instance
# =========================
@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance.
    Prevents reloading .env multiple times.
    """
    return Settings()