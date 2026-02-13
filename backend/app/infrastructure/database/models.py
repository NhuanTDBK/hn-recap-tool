"""SQLAlchemy ORM models for database tables."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, JSON, Numeric, String, Text, TIMESTAMP
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
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255))

    # User preferences
    interests = Column(JSON, default=list)  # List of interest topics
    memory_enabled = Column(Boolean, default=True)
    status = Column(String(50), default="active")  # active, paused, blocked

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    token_usage = relationship("UserTokenUsage", back_populates="user", cascade="all, delete-orphan")
    agent_calls = relationship("AgentCall", back_populates="user", cascade="all, delete-orphan")

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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)  # NULL = default/shared summary

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
        # Allows multiple prompt types per user, and shared summaries (user_id=NULL)
    )

    def __repr__(self):
        user_str = f"user_{self.user_id}" if self.user_id else "shared"
        return f"<Summary(post_id={self.post_id}, {user_str}, {self.prompt_type})>"
