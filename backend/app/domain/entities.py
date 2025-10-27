"""Domain entities - Core business objects with identity.

Using Pydantic for pragmatic validation, serialization, and less boilerplate.
These models represent core business concepts with built-in validation.
"""

from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from pydantic import BaseModel, Field, EmailStr, field_validator


class User(BaseModel):
    """User entity representing an authenticated user.

    Attributes:
        email: User's email address (unique identifier)
        hashed_password: Bcrypt hashed password
        created_at: Account creation timestamp
        is_active: Whether the account is active
        id: Unique identifier (auto-generated if not provided)
    """
    email: EmailStr
    hashed_password: str
    created_at: datetime
    is_active: bool = True
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()))

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "hashed_password": "$2b$12$...",
                "created_at": "2025-10-21T10:00:00",
                "is_active": True,
                "id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }
    }


class Post(BaseModel):
    """HackerNews post entity.

    Attributes:
        hn_id: Original HackerNews post ID
        title: Post title
        author: HN username of author
        points: Upvote count
        num_comments: Number of comments
        created_at: Post creation timestamp
        url: External URL (None for Ask HN/Show HN)
        post_type: Type of post (story, ask, show, job)
        content: Extracted article content (for display)
        raw_content: Full raw content (for processing)
        summary: AI-generated summary of the content
        collected_at: When we collected this post
        id: Unique identifier (auto-generated if not provided)
    """
    hn_id: int
    title: str
    author: str
    points: int = Field(ge=0)
    num_comments: int = Field(ge=0)
    created_at: datetime
    collected_at: datetime
    url: Optional[str] = None
    post_type: str = "story"
    content: Optional[str] = None
    raw_content: Optional[str] = None
    summary: Optional[str] = None
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()))

    @field_validator('post_type')
    @classmethod
    def validate_post_type(cls, v: str) -> str:
        """Validate post type is one of allowed values."""
        allowed_types = ['story', 'ask', 'show', 'job']
        if v not in allowed_types:
            raise ValueError(f"post_type must be one of {allowed_types}")
        return v

    def has_external_url(self) -> bool:
        """Check if post has an external URL."""
        return self.url is not None and self.url.strip() != ""

    def is_text_post(self) -> bool:
        """Check if this is a text-only post (Ask HN, Show HN)."""
        return not self.has_external_url()

    model_config = {
        "json_schema_extra": {
            "example": {
                "hn_id": 12345678,
                "title": "Show HN: My new project",
                "author": "pg",
                "points": 150,
                "num_comments": 42,
                "created_at": "2025-10-21T10:00:00",
                "collected_at": "2025-10-21T11:00:00",
                "url": "https://example.com",
                "post_type": "story",
                "id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }
    }


class Comment(BaseModel):
    """HackerNews comment entity.

    Attributes:
        hn_id: Original HackerNews comment ID
        post_id: ID of the post this comment belongs to
        author: HN username of comment author
        text: Comment text content
        points: Upvote count
        created_at: Comment creation timestamp
        parent_id: Parent comment ID (None for top-level)
        collected_at: When we collected this comment
        id: Unique identifier (auto-generated if not provided)
    """
    hn_id: int
    post_id: str
    author: str
    text: str
    points: int = Field(ge=0)
    created_at: datetime
    collected_at: datetime
    parent_id: Optional[int] = None
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()))

    def is_top_level(self) -> bool:
        """Check if this is a top-level comment."""
        return self.parent_id is None

    model_config = {
        "json_schema_extra": {
            "example": {
                "hn_id": 87654321,
                "post_id": "123e4567-e89b-12d3-a456-426614174000",
                "author": "user123",
                "text": "Great article!",
                "points": 5,
                "created_at": "2025-10-21T10:30:00",
                "collected_at": "2025-10-21T11:00:00",
                "parent_id": None,
                "id": "223e4567-e89b-12d3-a456-426614174000"
            }
        }
    }


class Digest(BaseModel):
    """Daily digest entity aggregating posts.

    Attributes:
        date: Date of the digest (YYYY-MM-DD)
        posts: List of posts in the digest
        created_at: Digest creation timestamp
        total_posts: Total number of posts
        id: Unique identifier (auto-generated if not provided)
    """
    date: str
    posts: List[Post] = Field(default_factory=list)
    created_at: datetime
    total_posts: int = 0
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()))

    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date is in YYYY-MM-DD format."""
        import re
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError("date must be in YYYY-MM-DD format")
        return v

    def model_post_init(self, __context) -> None:
        """Calculate total posts after initialization."""
        if self.total_posts == 0:
            self.total_posts = len(self.posts)

    def add_post(self, post: Post) -> None:
        """Add a post to the digest."""
        self.posts.append(post)
        self.total_posts = len(self.posts)

    def get_top_posts(self, limit: int = 10) -> List[Post]:
        """Get top N posts by points."""
        return sorted(self.posts, key=lambda p: p.points, reverse=True)[:limit]

    model_config = {
        "json_schema_extra": {
            "example": {
                "date": "2025-10-21",
                "posts": [],
                "created_at": "2025-10-21T12:00:00",
                "total_posts": 30,
                "id": "323e4567-e89b-12d3-a456-426614174000"
            }
        }
    }
