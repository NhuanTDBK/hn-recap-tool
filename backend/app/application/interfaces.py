"""Application interfaces (Ports) - Abstract contracts for infrastructure.

These define the contracts that infrastructure adapters must implement.
Following Dependency Inversion Principle: high-level modules (use cases)
depend on abstractions, not concrete implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Set
from datetime import datetime

from app.domain.entities import User, Post, Comment, Digest


# Repository Interfaces (Data Access)

class UserRepository(ABC):
    """Interface for user data persistence."""

    @abstractmethod
    async def save(self, user: User) -> User:
        """Save a user to storage.

        Args:
            user: User entity to save

        Returns:
            Saved user with generated ID
        """
        pass

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email address.

        Args:
            email: User's email address

        Returns:
            User if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_id(self, user_id: str) -> Optional[User]:
        """Find user by ID.

        Args:
            user_id: User's unique identifier

        Returns:
            User if found, None otherwise
        """
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update an existing user.

        Args:
            user: User entity with updated data

        Returns:
            Updated user
        """
        pass


class PostRepository(ABC):
    """Interface for post data persistence."""

    @abstractmethod
    async def save(self, post: Post) -> Post:
        """Save a post to storage.

        Args:
            post: Post entity to save

        Returns:
            Saved post with generated ID
        """
        pass

    @abstractmethod
    async def save_batch(self, posts: List[Post]) -> List[Post]:
        """Save multiple posts in batch.

        Args:
            posts: List of post entities to save

        Returns:
            List of saved posts
        """
        pass

    @abstractmethod
    async def find_by_id(self, post_id: str) -> Optional[Post]:
        """Find post by ID.

        Args:
            post_id: Post's unique identifier

        Returns:
            Post if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_hn_id(self, hn_id: int) -> Optional[Post]:
        """Find post by HackerNews ID.

        Args:
            hn_id: HackerNews post ID

        Returns:
            Post if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_existing_hn_ids(self, hn_ids: List[int]) -> Set[int]:
        """Find which HackerNews IDs already exist in storage.

        Args:
            hn_ids: List of HackerNews post IDs to check

        Returns:
            Set of IDs that already exist
        """
        pass

    @abstractmethod
    async def find_by_date(self, date: str) -> List[Post]:
        """Find all posts collected on a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            List of posts for that date
        """
        pass


class DigestRepository(ABC):
    """Interface for digest data persistence."""

    @abstractmethod
    async def save(self, digest: Digest) -> Digest:
        """Save a digest to storage.

        Args:
            digest: Digest entity to save

        Returns:
            Saved digest
        """
        pass

    @abstractmethod
    async def find_by_date(self, date: str) -> Optional[Digest]:
        """Find digest by date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Digest if found, None otherwise
        """
        pass

    @abstractmethod
    async def list_digests(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30
    ) -> List[Digest]:
        """List digests within a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            limit: Maximum number of digests to return

        Returns:
            List of digests
        """
        pass


class CommentRepository(ABC):
    """Interface for comment data persistence."""

    @abstractmethod
    async def save(self, comment: Comment) -> Comment:
        """Save a comment to storage.

        Args:
            comment: Comment entity to save

        Returns:
            Saved comment
        """
        pass

    @abstractmethod
    async def save_batch(self, comments: List[Comment]) -> List[Comment]:
        """Save multiple comments in batch.

        Args:
            comments: List of comment entities to save

        Returns:
            List of saved comments
        """
        pass

    @abstractmethod
    async def find_by_post_id(self, post_id: str) -> List[Comment]:
        """Find all comments for a specific post.

        Args:
            post_id: Post's unique identifier

        Returns:
            List of comments for that post
        """
        pass


class DeliveryRepository(ABC):
    """Interface for delivery tracking."""

    @abstractmethod
    async def save_delivery(
        self,
        user_id: int,
        post_id: str,
        batch_id: str,
        message_id: Optional[int] = None,
    ) -> dict:
        """Save a delivery record (post sent to user).

        Args:
            user_id: User who received the post
            post_id: Post that was delivered
            batch_id: Batch ID (groups posts in same digest)
            message_id: Telegram message ID (optional)

        Returns:
            Delivery record with ID
        """
        pass

    @abstractmethod
    async def find_deliveries_for_user(
        self,
        user_id: int,
        limit: int = 10,
    ) -> list:
        """Find recent deliveries for a user.

        Args:
            user_id: User ID
            limit: Maximum number of deliveries to return

        Returns:
            List of delivery records ordered by delivered_at DESC
        """
        pass

    @abstractmethod
    async def find_deliveries_for_batch(self, batch_id: str) -> list:
        """Find all deliveries in a batch.

        Args:
            batch_id: Batch ID

        Returns:
            List of delivery records for this batch
        """
        pass

    @abstractmethod
    async def update_reaction(
        self,
        delivery_id: str,
        reaction: str,
    ) -> dict:
        """Update user reaction to a delivered post.

        Args:
            delivery_id: Delivery record ID
            reaction: "up" | "down"

        Returns:
            Updated delivery record
        """
        pass

    @abstractmethod
    async def get_user_delivery_count(
        self,
        user_id: int,
        days: int = 7,
    ) -> int:
        """Count deliveries to user in past N days.

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Number of deliveries
        """
        pass


class ConversationRepository(ABC):
    """Interface for conversation/discussion storage."""

    @abstractmethod
    async def save_conversation(
        self,
        user_id: int,
        post_id: str,
        messages: list,
        token_usage: dict,
    ) -> dict:
        """Save a conversation record.

        Args:
            user_id: User in conversation
            post_id: Post being discussed
            messages: List of message dicts
            token_usage: Token usage dict

        Returns:
            Conversation record with ID
        """
        pass

    @abstractmethod
    async def find_active_conversation(self, user_id: int) -> Optional[dict]:
        """Find active conversation for user.

        Args:
            user_id: User ID

        Returns:
            Conversation record if active, None otherwise
        """
        pass

    @abstractmethod
    async def update_messages(
        self,
        conversation_id: str,
        messages: list,
    ) -> dict:
        """Update messages in a conversation.

        Args:
            conversation_id: Conversation ID
            messages: Updated message list

        Returns:
            Updated conversation record
        """
        pass

    @abstractmethod
    async def end_conversation(
        self,
        conversation_id: str,
        token_usage: dict,
    ) -> dict:
        """End a conversation and record token usage.

        Args:
            conversation_id: Conversation ID
            token_usage: Final token usage dict

        Returns:
            Ended conversation record
        """
        pass


# External Service Interfaces

class HNService(ABC):
    """Interface for HackerNews API client."""

    @abstractmethod
    async def fetch_front_page(self, limit: int = 30) -> List[dict]:
        """Fetch front page stories from HN.

        Args:
            limit: Maximum number of stories to fetch

        Returns:
            List of raw HN story data
        """
        pass

    @abstractmethod
    async def fetch_item(self, item_id: int) -> Optional[dict]:
        """Fetch a specific item (story/comment) by ID.

        Args:
            item_id: HN item ID

        Returns:
            Raw HN item data if found
        """
        pass

    @abstractmethod
    async def fetch_comments(self, post_id: int, limit: int = 50) -> List[dict]:
        """Fetch comments for a specific post.

        Args:
            post_id: HN post ID
            limit: Maximum number of comments to fetch

        Returns:
            List of raw HN comment data
        """
        pass


class ContentExtractor(ABC):
    """Interface for article content extraction."""

    @abstractmethod
    async def extract_content(self, url: str) -> Optional[str]:
        """Extract main content from a URL.

        Args:
            url: Article URL to extract from

        Returns:
            Extracted text content if successful
        """
        pass


class ContentRepository(ABC):
    """Interface for content storage and retrieval."""

    @abstractmethod
    async def save_text_content(self, hn_id: int, content: str) -> None:
        """Save text content for a post.

        Args:
            hn_id: HackerNews post ID
            content: Extracted text content
        """
        pass

    @abstractmethod
    async def save_html_content(self, hn_id: int, html: str) -> None:
        """Save HTML content for a post.

        Args:
            hn_id: HackerNews post ID
            html: Raw HTML content
        """
        pass

    @abstractmethod
    async def get_text_content(self, hn_id: int) -> Optional[str]:
        """Retrieve text content for a post.

        Args:
            hn_id: HackerNews post ID

        Returns:
            Text content if exists, None otherwise
        """
        pass

    @abstractmethod
    async def get_html_content(self, hn_id: int) -> Optional[str]:
        """Retrieve HTML content for a post.

        Args:
            hn_id: HackerNews post ID

        Returns:
            HTML content if exists, None otherwise
        """
        pass

    @abstractmethod
    async def text_content_exists(self, hn_id: int) -> bool:
        """Check if text content exists for a post.

        Args:
            hn_id: HackerNews post ID

        Returns:
            True if text content exists, False otherwise
        """
        pass

    @abstractmethod
    async def html_content_exists(self, hn_id: int) -> bool:
        """Check if HTML content exists for a post.

        Args:
            hn_id: HackerNews post ID

        Returns:
            True if HTML content exists, False otherwise
        """
        pass


class CacheService(ABC):
    """Interface for caching service."""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if exists
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int = 3600) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key to delete
        """
        pass


# Authentication & Security Interfaces

class PasswordHasher(ABC):
    """Interface for password hashing."""

    @abstractmethod
    def hash(self, password: str) -> str:
        """Hash a plain text password.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        pass

    @abstractmethod
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        pass


class TokenService(ABC):
    """Interface for JWT token management."""

    @abstractmethod
    def create_access_token(self, data: dict, expires_delta: Optional[int] = None) -> str:
        """Create a JWT access token.

        Args:
            data: Data to encode in token
            expires_delta: Token expiration time in minutes

        Returns:
            Encoded JWT token
        """
        pass

    @abstractmethod
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode a JWT token.

        Args:
            token: JWT token to verify

        Returns:
            Decoded token data if valid, None otherwise
        """
        pass


class SummarizationService(ABC):
    """Interface for AI-powered content summarization."""

    @abstractmethod
    async def summarize(self, content: str) -> str:
        """Generate a summary of the given content.

        Args:
            content: Text content to summarize

        Returns:
            Generated summary

        Raises:
            Exception: If summarization fails
        """
        pass

    @abstractmethod
    async def summarize_batch(self, contents: List[str]) -> List[str]:
        """Generate summaries for multiple content items.

        Args:
            contents: List of text contents to summarize

        Returns:
            List of generated summaries in the same order

        Raises:
            Exception: If summarization fails
        """
        pass


class SynthesisSummarizationService(ABC):
    """Interface for synthesizing summaries from multiple posts."""

    @abstractmethod
    async def synthesize(self, posts: List[Post]) -> str:
        """Generate a synthesis summary from multiple posts.

        Args:
            posts: List of Post entities to synthesize

        Returns:
            Synthesized summary combining insights from all posts

        Raises:
            Exception: If synthesis fails
        """
        pass

    @abstractmethod
    async def synthesize_by_topic(self, posts: List[Post], topic: str) -> str:
        """Generate a topic-focused synthesis from multiple posts.

        Args:
            posts: List of Post entities to synthesize
            topic: Topic or theme to focus on

        Returns:
            Topic-focused synthesized summary

        Raises:
            Exception: If synthesis fails
        """
        pass

    @abstractmethod
    async def synthesize_from_summaries(self, summaries: List[dict]) -> str:
        """Generate a synthesis from individual post summaries.

        Args:
            summaries: List of dicts with 'title', 'summary', and optional 'url'

        Returns:
            Synthesized summary combining all individual summaries

        Raises:
            Exception: If synthesis fails
        """
        pass
