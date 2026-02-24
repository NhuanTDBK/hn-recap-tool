"""Application configuration using Pydantic Settings.

Loads configuration from environment variables and .env file.
"""

import logging
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


logger = logging.getLogger(__name__)


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
    data_dir: str = "data"
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
    openai_model: str = "gpt-5-nano"
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.3
    summarization_enabled: bool = True
    summarization_chunk_size: int = 8000
    summarization_max_chunk_tokens: int = 4000

    # Delivery Optimization
    enable_grouped_delivery: bool = False  # Feature flag: use optimized delivery pipeline
    grouped_delivery_batch_size: int = 10  # Posts per LLM batch call
    grouped_delivery_max_styles: int = 50  # Safety limit on number of styles

    # Telegram Bot
    telegram_bot_token: Optional[str] = None

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Logging
    log_level: str = "INFO"

    @field_validator("data_dir", mode="before")
    @classmethod
    def resolve_data_dir(cls, value: str) -> str:
        """Resolve data directory to an absolute path.

        Preference order:
        1) If absolute, keep as-is.
        2) If relative, resolve against the project root (directory containing
           .git or data). If not found, fall back to cwd.
        """

        path = Path(value)
        if path.is_absolute():
            resolved = path
        else:
            current = Path(__file__).resolve()
            project_root: Optional[Path] = None
            while current.parent != current:
                if (current / ".git").exists() or (current / "data").exists():
                    project_root = current
                    break
                current = current.parent

            base = project_root or Path.cwd()
            resolved = (base / path).resolve()

        logger.info("Resolved data_dir to %s", resolved)
        return str(resolved)


# Global settings instance
settings = Settings()
