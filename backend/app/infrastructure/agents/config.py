"""Agent configuration using Pydantic Settings."""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Configuration for AI agents and LLM services."""

    model_config = SettingsConfigDict(
        env_file="backend/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_default_temperature: float = 0.7
    openai_default_max_tokens: int = 500

    # Langfuse Configuration (Observability)
    langfuse_enabled: bool = True
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # Retry Configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff_factor: float = 2.0

    # Rate Limiting
    rate_limit_requests_per_minute: int = 60

    # Cost Tracking
    track_token_usage: bool = True
    cost_alert_threshold_usd: float = 5.0  # Alert if daily cost exceeds this


# Global settings instance
settings = AgentSettings()
