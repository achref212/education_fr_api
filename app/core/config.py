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

    # Local media uploads. Files live on disk; database rows store URLs/metadata.
    media_root: str = Field(default="storage/media", validation_alias="MEDIA_ROOT")
    media_url_prefix: str = Field(default="/media", validation_alias="MEDIA_URL_PREFIX")
    max_image_mb: int = Field(default=5, validation_alias="MAX_IMAGE_MB")
    max_audio_mb: int = Field(default=50, validation_alias="MAX_AUDIO_MB")
    max_document_mb: int = Field(default=20, validation_alias="MAX_DOCUMENT_MB")

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

    # AI content generation
    ai_provider: str = Field(default="hf", validation_alias="AI_PROVIDER")
    ai_backup_provider: str = Field(
        default="nvidia", validation_alias="AI_BACKUP_PROVIDER"
    )
    hf_token: str = Field(default="", validation_alias="HF_TOKEN")
    nvidia_api_key: str = Field(default="", validation_alias="NVIDIA_API_KEY")
    ai_model: str = Field(
        default="Qwen/Qwen2.5-7B-Instruct", validation_alias="AI_MODEL"
    )
    ai_backup_model: str = Field(
        default="meta/llama-3.1-8b-instruct",
        validation_alias="AI_BACKUP_MODEL",
    )
    ai_timeout_seconds: float = Field(default=45.0, validation_alias="AI_TIMEOUT_SECONDS")
    ai_repair_retries: int = Field(default=1, validation_alias="AI_REPAIR_RETRIES")


@lru_cache
def get_settings() -> Settings:
    return Settings()
