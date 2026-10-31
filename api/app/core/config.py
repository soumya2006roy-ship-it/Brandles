from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"
    app_secret_key: str = "local-only-change-me"
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0
    database_url: str = "postgresql+psycopg://brandlens:brandlens@localhost:5432/brandlens"
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_multiplier: float = Field(default=1.0, gt=0, le=10)
    trusted_proxy_cidrs: str = ""
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
    malware_scanner_host: str | None = None
    malware_scanner_port: int = 3310
    malware_scan_timeout_seconds: int = 10
    s3_endpoint_url: str | None = None
    s3_bucket: str = "brandlens-private"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_region: str = "us-east-1"
    s3_signed_url_ttl_seconds: int = 300
    llm_provider: str = "none"
    llm_model: str = "none"
    llm_api_key: str | None = None
    llm_timeout_seconds: int = 30
    llm_max_tokens: int = 1200
    scan_max_assets: int = 100
    scan_max_claims: int = 100
    scan_timeout_seconds: int = 300
    embedding_provider: str = "none"
    embedding_model: str = "none"
    embedding_api_key: str | None = None
    embedding_dimensions: int = 1536
    ocr_provider: str = "none"
    tesseract_command: str | None = None
    tesseract_timeout_seconds: int = 20
    visual_confidence_threshold: float = Field(default=0.65, ge=0, le=1)
    allow_workspace_llm: bool = False
    password_reset_ttl_minutes: int = 30
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
