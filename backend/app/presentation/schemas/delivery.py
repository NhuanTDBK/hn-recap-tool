"""Response schemas for delivery endpoints."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class DeliveryErrorItem(BaseModel):
    """Delivery error item."""

    user_id: Optional[int] = Field(None, description="User ID (if applicable)")
    stage: Optional[str] = Field(None, description="Pipeline stage where error occurred")
    error: str = Field(..., description="Error message (truncated to 100 chars)")


class DeliveryPipelineRequest(BaseModel):
    """Request body for delivery pipeline execution."""

    batch_id: Optional[str] = Field(
        None, description="Batch ID (optional, generated if not provided)"
    )
    max_posts_per_user: int = Field(
        10, ge=1, le=100, description="Maximum posts per user"
    )
    skip_user_ids: Optional[List[int]] = Field(
        None, description="User IDs to skip"
    )
    dry_run: bool = Field(
        False, description="If True, don't send messages or update DB"
    )


class DeliveryPipelineResponse(BaseModel):
    """Response from delivery pipeline execution."""

    batch_id: str = Field(..., description="Batch ID")
    total_users: int = Field(..., description="Total active users")
    users_delivered: int = Field(..., description="Users who received delivery")
    users_skipped: int = Field(..., description="Users skipped (no posts or errors)")
    total_messages_sent: int = Field(
        ..., description="Total Telegram messages sent"
    )
    total_posts_delivered: int = Field(..., description="Total posts delivered")
    errors: List[DeliveryErrorItem] = Field(
        default_factory=list, description="List of errors (if any)"
    )
    start_time: str = Field(..., description="Pipeline start time (ISO format)")
    end_time: str = Field(..., description="Pipeline end time (ISO format)")
    duration_seconds: float = Field(..., description="Total execution time in seconds")

    class Config:
        """Pydantic config."""
        from_attributes = True
