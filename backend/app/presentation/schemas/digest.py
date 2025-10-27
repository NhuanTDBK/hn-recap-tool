"""Pydantic schemas for digest-related API requests and responses."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class PostResponse(BaseModel):
    """Schema for post in API response."""
    id: str
    hn_id: int
    title: str
    author: str
    points: int
    num_comments: int
    created_at: datetime
    url: Optional[str] = None
    post_type: str
    content: Optional[str] = None  # Preview only
    summary: Optional[str] = None  # AI-generated summary

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "hn_id": 12345678,
                "title": "Show HN: My new project",
                "author": "pg",
                "points": 150,
                "num_comments": 42,
                "created_at": "2025-10-21T10:00:00",
                "url": "https://example.com",
                "post_type": "story",
                "content": "This is a preview of the article content..."
            }
        }
    }


class PostDetailResponse(BaseModel):
    """Schema for detailed post response (includes full content)."""
    id: str
    hn_id: int
    title: str
    author: str
    points: int
    num_comments: int
    created_at: datetime
    url: Optional[str] = None
    post_type: str
    content: Optional[str] = None
    raw_content: Optional[str] = None  # Full content
    summary: Optional[str] = None  # AI-generated summary
    collected_at: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "hn_id": 12345678,
                "title": "Show HN: My new project",
                "author": "pg",
                "points": 150,
                "num_comments": 42,
                "created_at": "2025-10-21T10:00:00",
                "url": "https://example.com",
                "post_type": "story",
                "content": "Preview...",
                "raw_content": "Full article content here...",
                "collected_at": "2025-10-21T11:00:00"
            }
        }
    }


class DigestResponse(BaseModel):
    """Schema for digest response."""
    id: str
    date: str
    total_posts: int
    created_at: datetime
    posts: List[PostResponse]

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "323e4567-e89b-12d3-a456-426614174000",
                "date": "2025-10-21",
                "total_posts": 30,
                "created_at": "2025-10-21T12:00:00",
                "posts": []
            }
        }
    }


class DigestListItem(BaseModel):
    """Schema for digest list item (summary only, no posts)."""
    id: str
    date: str
    total_posts: int
    created_at: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "323e4567-e89b-12d3-a456-426614174000",
                "date": "2025-10-21",
                "total_posts": 30,
                "created_at": "2025-10-21T12:00:00"
            }
        }
    }


class DigestListResponse(BaseModel):
    """Schema for list of digests."""
    digests: List[DigestListItem]
    total: int = Field(description="Total number of digests returned")

    model_config = {
        "json_schema_extra": {
            "example": {
                "digests": [],
                "total": 30
            }
        }
    }
