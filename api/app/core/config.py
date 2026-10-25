from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"
    app_secret_key: str = "local-only-change-me"
    database_url: str = "postgresql+psycopg://brandlens:brandlens@localhost:5432/brandlens"
    redis_url: str = "redis://localhost:6379/0"
    frontend_origin: str = "http://localhost:3000"
    session_cookie_name: str = "brandlens_session"
    session_ttl_hours: int = 12
    session_cookie_secure: bool = False
    email_provider: str = "resend"
    resend_api_key: str | None = None
    resend_from_email: str = "BrandLens <hello@example.com>"
    smtp_host: str | None = None
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = False
    file_storage_driver: str = "local"
    local_storage_path: str = "./private-uploads"
    s3_endpoint_url: str | None = None
    s3_bucket: str = "brandlens-private"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_region: str = "us-east-1"
    s3_signed_url_ttl_seconds: int = 300
    llm_provider: str = "mock"
    llm_model: str = "mock"
    llm_api_key: str | None = None
    llm_timeout_seconds: int = 30
    llm_max_tokens: int = 1200
    embedding_provider: str = "mock"
    embedding_model: str = "mock"
    embedding_api_key: str | None = None
    embedding_dimensions: int = 1536
    allow_workspace_llm: bool = False
    verification_token_ttl_minutes: int = 60
    password_reset_ttl_minutes: int = 30

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
