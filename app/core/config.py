from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        default="postgresql://user:password@localhost:5432/education_fr",
        validation_alias="DATABASE_URL",
    )
    secret_key: str = Field(default="change-me", validation_alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", validation_alias="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=10080, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    cors_origins: str = Field(default="*", validation_alias="CORS_ORIGINS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
