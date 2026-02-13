"""Application configuration using Pydantic Settings.

Loads configuration from environment variables and .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )
    # Application
    app_name: str = "HackerNews Digest"
    app_version: str = "1.0.0"
    debug: bool = False

    # Security
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Database
    database_url: str = "postgresql+asyncpg://hn_pal:hn_pal_dev@localhost:5433/hn_pal"

    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_ttl: int = 3600  # 1 hour default TTL

    # Data Storage
    data_dir: str = "../data"
    user_data_file: str = "users/user-profiles.jsonl"

    # HackerNews API
    hn_api_base_url: str = "http://hn.algolia.com/api/v1"
    hn_api_timeout: int = 10
    hn_max_posts: int = 30
    hn_max_comments: int = 50

    # Content Extraction
    content_extraction_timeout: int = 15

    # AI Summarization
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.3
    summarization_enabled: bool = True
    summarization_chunk_size: int = 8000
    summarization_max_chunk_tokens: int = 4000

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Logging
    log_level: str = "INFO"


# Global settings instance
settings = Settings()
