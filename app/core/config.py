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

    # SMTP / email
    smtp_host: str = Field(default="", validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_username: str = Field(default="", validation_alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", validation_alias="SMTP_PASSWORD")
    # smtp_use_ssl=True  → port 465, smtplib.SMTP_SSL  (Gmail legacy SSL)
    # smtp_use_tls=True  → port 587, STARTTLS upgrade   (most modern providers)
    smtp_use_ssl: bool = Field(default=False, validation_alias="SMTP_USE_SSL")
    smtp_use_tls: bool = Field(default=True, validation_alias="SMTP_USE_TLS")
    smtp_from_email: str = Field(
        default="no-reply@delfy.app", validation_alias="SMTP_FROM_EMAIL"
    )
    smtp_from_name: str = Field(
        default="DELFy", validation_alias="SMTP_FROM_NAME"
    )

    # Password reset
    password_reset_code_expire_minutes: int = Field(
        default=15, validation_alias="PASSWORD_RESET_CODE_EXPIRE_MINUTES"
    )

    # Dashboard URL sent in welcome emails (school / prof)
    dashboard_url: str = Field(
        default="https://dashboard.delfy.app", validation_alias="DASHBOARD_URL"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
