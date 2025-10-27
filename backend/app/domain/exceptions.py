"""Domain exceptions - Business rule violations and domain-specific errors.

These exceptions represent violations of business rules and domain constraints.
They should be caught at the application/presentation layer and translated to
appropriate HTTP responses or error messages.
"""


class DomainException(Exception):
    """Base exception for all domain-level errors."""
    pass


# User-related exceptions
class UserException(DomainException):
    """Base exception for user-related errors."""
    pass


class UserAlreadyExistsError(UserException):
    """Raised when attempting to create a user that already exists."""
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"User with email {email} already exists")


class UserNotFoundError(UserException):
    """Raised when a user cannot be found."""
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"User with email {email} not found")


class InvalidCredentialsError(UserException):
    """Raised when login credentials are invalid."""
    def __init__(self):
        super().__init__("Invalid email or password")


class InactiveUserError(UserException):
    """Raised when attempting to authenticate an inactive user."""
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"User {email} is inactive")


# Post-related exceptions
class PostException(DomainException):
    """Base exception for post-related errors."""
    pass


class PostNotFoundError(PostException):
    """Raised when a post cannot be found."""
    def __init__(self, post_id: str):
        self.post_id = post_id
        super().__init__(f"Post with ID {post_id} not found")


class InvalidPostDataError(PostException):
    """Raised when post data is invalid or incomplete."""
    def __init__(self, message: str):
        super().__init__(f"Invalid post data: {message}")


# Digest-related exceptions
class DigestException(DomainException):
    """Base exception for digest-related errors."""
    pass


class DigestNotFoundError(DigestException):
    """Raised when a digest cannot be found for a specific date."""
    def __init__(self, date: str):
        self.date = date
        super().__init__(f"Digest for date {date} not found")


class DigestAlreadyExistsError(DigestException):
    """Raised when attempting to create a digest that already exists."""
    def __init__(self, date: str):
        self.date = date
        super().__init__(f"Digest for date {date} already exists")


class EmptyDigestError(DigestException):
    """Raised when attempting to create a digest with no posts."""
    def __init__(self, date: str):
        self.date = date
        super().__init__(f"Cannot create empty digest for {date}")


# Comment-related exceptions
class CommentException(DomainException):
    """Base exception for comment-related errors."""
    pass


class CommentNotFoundError(CommentException):
    """Raised when a comment cannot be found."""
    def __init__(self, comment_id: str):
        self.comment_id = comment_id
        super().__init__(f"Comment with ID {comment_id} not found")


# Collection-related exceptions
class CollectionException(DomainException):
    """Base exception for data collection errors."""
    pass


class HNAPIError(CollectionException):
    """Raised when HackerNews API request fails."""
    def __init__(self, message: str):
        super().__init__(f"HN API error: {message}")


class ContentExtractionError(CollectionException):
    """Raised when content extraction fails."""
    def __init__(self, url: str, reason: str):
        self.url = url
        self.reason = reason
        super().__init__(f"Failed to extract content from {url}: {reason}")


class RateLimitExceededError(CollectionException):
    """Raised when API rate limit is exceeded."""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds")


# Storage-related exceptions
class StorageException(DomainException):
    """Base exception for storage-related errors."""
    pass


class StorageReadError(StorageException):
    """Raised when reading from storage fails."""
    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to read from {path}: {reason}")


class StorageWriteError(StorageException):
    """Raised when writing to storage fails."""
    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to write to {path}: {reason}")
