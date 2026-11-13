"""SQLAlchemy ORM models for database tables."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.infrastructure.database.base import Base


class Post(Base):
    """Post model representing HackerNews posts."""

    __tablename__ = "posts"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # HN metadata
    hn_id = Column(Integer, unique=True, nullable=False, index=True)
    type = Column(String, nullable=False, index=True, default="story")  # story, ask, show, job
    title = Column(Text)
    author = Column(String)
    url = Column(Text)
    domain = Column(String)  # extracted from URL
    score = Column(Integer, default=0, index=True)
    comment_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    collected_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Filtering flags
    is_dead = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)

    # Content flags (track if content exists in RocksDB)
    has_html = Column(Boolean, default=False)
    has_text = Column(Boolean, default=False)
    has_markdown = Column(Boolean, default=False)

    # Crawl tracking
    is_crawl_success = Column(Boolean, default=False)
    crawl_retry_count = Column(Integer, default=0)
    crawl_error = Column(Text)
    crawled_at = Column(TIMESTAMP(timezone=True))
    content_length = Column(Integer)  # Length of extracted text

    # Summary (populated by summarization pipeline)
    summary = Column(Text)
    summarized_at = Column(TIMESTAMP(timezone=True))

    # Metadata
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self):
        return f"<Post(hn_id={self.hn_id}, title='{self.title[:50]}...')>"


class User(Base):
    """User model for Telegram bot users."""

    __tablename__ = "users"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Telegram identity
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255))

    # User preferences
    interests = Column(JSON, default=list)  # List of interest topics
    memory_enabled = Column(Boolean, default=True)
    status = Column(String(50), default="active")  # active, paused, blocked
    delivery_style = Column(String(50), default="flat_scroll")  # flat_scroll, brief
    summary_preferences = Column(
        JSON,
        nullable=False,
        default={"style": "basic", "detail_level": "medium", "technical_depth": "intermediate"}
    )  # Summary style configuration

    # Delivery tracking
    last_delivered_at = Column(TIMESTAMP(timezone=True), nullable=True)  # When user last received digest

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    summaries = relationship("Summary", back_populates="user", cascade="all, delete-orphan")
    token_usage = relationship("UserTokenUsage", back_populates="user", cascade="all, delete-orphan")
    agent_calls = relationship("AgentCall", back_populates="user", cascade="all, delete-orphan")
    deliveries = relationship("Delivery", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    activity_log = relationship("UserActivityLog", back_populates="user", cascade="all, delete-orphan")

    def get_summary_style(self) -> str:
        """Get the user's preferred summary style."""
        if self.summary_preferences and isinstance(self.summary_preferences, dict):
            return self.summary_preferences.get("style", "basic")
        return "basic"

    def update_summary_preferences(self, **kwargs) -> None:
        """Update summary preferences with new values."""
        if not self.summary_preferences:
            self.summary_preferences = {
                "style": "basic",
                "detail_level": "medium",
                "technical_depth": "intermediate"
            }

        # Assign a new dict: SQLAlchemy does not detect in-place changes to a plain JSON column,
        # so mutating the existing dict would never be written to the database.
        updated = dict(self.summary_preferences)
        updated.update(kwargs)
        self.summary_preferences = updated

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username='{self.username}')>"


class UserTokenUsage(Base):
    """Per-user daily token usage tracking for cost monitoring."""

    __tablename__ = "user_token_usage"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Foreign key
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Tracking data
    date = Column(Date, nullable=False, index=True)
    model = Column(String(50), nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Numeric(10, 6), default=Decimal("0"))
    request_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="token_usage")

    __table_args__ = ()

    def __repr__(self):
        return f"<UserTokenUsage(user_id={self.user_id}, date={self.date}, tokens={self.total_tokens})>"


class AgentCall(Base):
    """Individual agent call tracking for detailed logging and debugging."""

    __tablename__ = "agent_calls"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Foreign key
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)

    # Call details
    trace_id = Column(String(255), index=True)  # Langfuse trace ID
    agent_name = Column(String(100), nullable=False, index=True)
    operation = Column(String(100))  # e.g., summarize_post, answer_question
    model = Column(String(50), nullable=False)

    # Token usage
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    total_tokens = Column(Integer)
    cost_usd = Column(Numeric(10, 6))

    # Performance
    latency_ms = Column(Integer)  # Response time in milliseconds
    status = Column(String(20), default="success")  # success, error

    # Error tracking
    error_message = Column(Text)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="agent_calls")

    def __repr__(self):
        return f"<AgentCall(agent={self.agent_name}, operation={self.operation}, status={self.status})>"


class Summary(Base):
    """Personalized summaries for posts - supports different users and prompt types."""

    __tablename__ = "summaries"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Foreign keys
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # Required for personalization

    # Summary details
    prompt_type = Column(String(50), nullable=False, index=True)  # basic, technical, business, concise, personalized
    summary_text = Column(Text, nullable=False)  # The actual summary content
    key_points = Column(JSON, default=list)  # Extracted key points if structured output used
    technical_level = Column(String(50))  # beginner, intermediate, advanced

    # Cost tracking
    token_count = Column(Integer)  # Total tokens used for this summary
    cost_usd = Column(Numeric(10, 6))  # Cost of generation

    # User feedback for improvement
    rating = Column(Integer)  # 1-5 star rating from user
    user_feedback = Column(Text)  # User feedback text

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    post = relationship("Post")
    user = relationship("User")

    __table_args__ = (
        # Unique constraint: one summary per post/user/prompt_type combo
        # Prevents duplicate summaries for same post/user/type
    )

    def __repr__(self):
        return f"<Summary(post_id={self.post_id}, user_{self.user_id}, {self.prompt_type})>"


class Delivery(Base):
    """Tracks which posts were delivered to which users via Telegram."""

    __tablename__ = "deliveries"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)

    # Delivery metadata
    message_id = Column(Integer, nullable=True)  # Telegram message ID
    batch_id = Column(String(36), nullable=False, index=True)  # UUID string - groups posts in same digest
    reaction = Column(String(10), nullable=True)  # "up" | "down" | null (user reaction)

    # Timestamps
    delivered_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="deliveries")
    post = relationship("Post")

    def __repr__(self):
        return f"<Delivery(user_id={self.user_id}, post_id={self.post_id}, batch_id={self.batch_id})>"


class Conversation(Base):
    """Stores discussion threads per user per post (or general topic if post_id is null)."""

    __tablename__ = "conversations"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=True, index=True)

    # Conversation data
    messages = Column(JSON, default=list)  # [{role, content, timestamp}, ...]
    token_usage = Column(JSON, default=dict)  # {input_tokens, output_tokens, model}

    # Timestamps
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), index=True)
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="conversations")
    post = relationship("Post")

    __table_args__ = (
        # At most one active conversation (ended_at IS NULL) per user.
        Index(
            "uq_conversations_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    def __repr__(self):
        status = "active" if self.ended_at is None else "ended"
        pid = self.post_id or "topic"
        return f"<Conversation(user_id={self.user_id}, post_id={pid}, status={status})>"


class UserActivityLog(Base):
    """Append-only log of user interactions: rating summaries and saving posts."""

    __tablename__ = "user_activity_log"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)

    # Activity details
    action_type = Column(String(20), nullable=False, index=True)  # "rate_up", "rate_down", "save"

    # Timestamp
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="activity_log")
    post = relationship("Post")

    def __repr__(self):
        return f"<UserActivityLog(user_id={self.user_id}, post_id={self.post_id}, action={self.action_type}, at={self.created_at})>"


class RecommendationRun(Base):
    """One daily recommendation run: what the model inferred and what it was given.

    Never overwritten, so changes in inferred interests can be tracked over time.
    """

    __tablename__ = "recommendation_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    run_date = Column(Date, nullable=False, index=True)  # local date in RECOMMENDATION_TIMEZONE

    interests = Column(JSON, default=list)  # interests the model inferred from the signals
    saved_count = Column(Integer, default=0)
    not_for_me_count = Column(Integer, default=0)
    opened_count = Column(Integer, default=0)
    ignored_count = Column(Integer, default=0)
    candidate_count = Column(Integer, default=0)

    model = Column(String(100))
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User")
    recommendations = relationship("Recommendation", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RecommendationRun(user_id={self.user_id}, run_date={self.run_date})>"


class Recommendation(Base):
    """A post picked for a user by the daily recommendation run.

    Kept apart from ``deliveries`` on purpose: a delivery row would hide the post from
    the Streaming feed and break the reaction handlers, which expect one row per post.
    """

    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("recommendation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)

    recommended_on = Column(Date, nullable=False, index=True)  # local date in RECOMMENDATION_TIMEZONE
    rank = Column(Integer, nullable=False)
    fit_score = Column(Integer, nullable=False)  # 1-5, from the model
    reason = Column(Text, nullable=False)  # shown by the "Why" button

    topic = Column(String(60), nullable=True)  # short topic label from the model; NULL on picks made before exploring
    kind = Column(String(10), nullable=False, default="exploit", server_default="exploit")  # "exploit" or "explore"
    quality = Column(Integer, nullable=True)  # 1-5 taste-independent quality; set on explore picks

    message_id = Column(Integer, nullable=True)  # Telegram message ID, set once sent
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)  # NULL = picked but not sent yet

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    run = relationship("RecommendationRun", back_populates="recommendations")
    post = relationship("Post")

    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="uq_recommendations_user_post"),
        Index("ix_recommendations_user_topic", "user_id", "topic"),
    )

    def __repr__(self):
        return f"<Recommendation(user_id={self.user_id}, post_id={self.post_id}, fit={self.fit_score})>"
