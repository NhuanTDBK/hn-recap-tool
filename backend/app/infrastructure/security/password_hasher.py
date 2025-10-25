"""Password hashing implementation using bcrypt."""

from passlib.context import CryptContext
from app.application.interfaces import PasswordHasher


class BcryptPasswordHasher(PasswordHasher):
    """Password hasher using bcrypt algorithm."""

    def __init__(self):
        """Initialize bcrypt context."""
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash(self, password: str) -> str:
        """Hash a plain text password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return self.pwd_context.hash(password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a bcrypt hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        return self.pwd_context.verify(plain_password, hashed_password)
