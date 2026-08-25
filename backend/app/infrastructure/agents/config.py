"""Agent configuration using Pydantic Settings."""

from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Configuration for AI agents and LLM services."""

    model_config = SettingsConfigDict(
        env_file="backend/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from environment
    )

    # LLM provider configuration.
    # Gemini via its OpenAI-compatible endpoint (same approach as receipt-pal):
    # point the OpenAI Agents SDK at Gemini's base_url with a Gemini API key.
    openai_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("openai_api_key", "gemini_api_key"),
    )
    openai_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai/",
        validation_alias=AliasChoices("openai_base_url", "gemini_base_url"),
    )
    openai_model: str = "gemini-3.6-flash"
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

    # Context Window Management
    context_window_tokens: int = (
        80000  # Max tokens for agent context (system + history + tool output)
    )

    # Cost Tracking
    track_token_usage: bool = True
    cost_alert_threshold_usd: float = 5.0  # Alert if daily cost exceeds this


# Global settings instance
settings = AgentSettings()
