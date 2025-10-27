"""JSONL implementation of UserRepository."""

from pathlib import Path
from typing import Optional
import logging

from app.domain.entities import User
from app.application.interfaces import UserRepository
from app.infrastructure.repositories.jsonl_helpers import (
    read_jsonl,
    write_jsonl,
    find_by_field,
    update_record
)

logger = logging.getLogger(__name__)


class JSONLUserRepository(UserRepository):
    """User repository using JSONL file storage."""

    def __init__(self, file_path: str):
        """Initialize repository.

        Args:
            file_path: Path to JSONL file for user storage
        """
        self.file_path = file_path
        logger.info(f"Initialized JSONLUserRepository with file: {file_path}")

    async def save(self, user: User) -> User:
        """Save a user to JSONL storage.

        Args:
            user: User entity to save

        Returns:
            Saved user
        """
        user_data = user.model_dump()
        write_jsonl(self.file_path, user_data, append=True)
        logger.info(f"Saved user: {user.email}")
        return user

    async def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email address.

        Args:
            email: User's email address

        Returns:
            User if found, None otherwise
        """
        if not Path(self.file_path).exists():
            return None

        record = find_by_field(self.file_path, "email", email)
        if record:
            return User(**record)
        return None

    async def find_by_id(self, user_id: str) -> Optional[User]:
        """Find user by ID.

        Args:
            user_id: User's unique identifier

        Returns:
            User if found, None otherwise
        """
        if not Path(self.file_path).exists():
            return None

        record = find_by_field(self.file_path, "id", user_id)
        if record:
            return User(**record)
        return None

    async def update(self, user: User) -> User:
        """Update an existing user.

        Args:
            user: User entity with updated data

        Returns:
            Updated user
        """
        user_data = user.model_dump()
        updated = update_record(self.file_path, "id", user.id, user_data)

        if not updated:
            # If not found, save as new
            await self.save(user)

        logger.info(f"Updated user: {user.email}")
        return user
