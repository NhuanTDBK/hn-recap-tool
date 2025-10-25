"""Authentication use cases - User registration and login business logic."""

from datetime import datetime
from typing import Tuple

from app.domain.entities import User
from app.domain.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
    InvalidCredentialsError,
    InactiveUserError
)
from app.application.interfaces import (
    UserRepository,
    PasswordHasher,
    TokenService
)


class RegisterUserUseCase:
    """Use case for user registration."""

    def __init__(
        self,
        user_repo: UserRepository,
        password_hasher: PasswordHasher
    ):
        self.user_repo = user_repo
        self.password_hasher = password_hasher

    async def execute(self, email: str, password: str) -> User:
        """Register a new user.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            Created user entity

        Raises:
            UserAlreadyExistsError: If user with email already exists
        """
        # Check if user already exists
        existing_user = await self.user_repo.find_by_email(email)
        if existing_user:
            raise UserAlreadyExistsError(email)

        # Hash password
        hashed_password = self.password_hasher.hash(password)

        # Create user entity
        user = User(
            email=email,
            hashed_password=hashed_password,
            created_at=datetime.utcnow(),
            is_active=True
        )

        # Save to repository
        saved_user = await self.user_repo.save(user)
        return saved_user


class LoginUserUseCase:
    """Use case for user login."""

    def __init__(
        self,
        user_repo: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService
    ):
        self.user_repo = user_repo
        self.password_hasher = password_hasher
        self.token_service = token_service

    async def execute(self, email: str, password: str) -> Tuple[User, str]:
        """Authenticate user and generate access token.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            Tuple of (authenticated user, access token)

        Raises:
            UserNotFoundError: If user doesn't exist
            InvalidCredentialsError: If password is incorrect
            InactiveUserError: If user account is inactive
        """
        # Find user by email
        user = await self.user_repo.find_by_email(email)
        if not user:
            raise InvalidCredentialsError()

        # Verify password
        if not self.password_hasher.verify(password, user.hashed_password):
            raise InvalidCredentialsError()

        # Check if user is active
        if not user.is_active:
            raise InactiveUserError(email)

        # Generate access token
        token_data = {"sub": user.email, "user_id": user.id}
        access_token = self.token_service.create_access_token(token_data)

        return user, access_token


class GetCurrentUserUseCase:
    """Use case for retrieving current authenticated user."""

    def __init__(
        self,
        user_repo: UserRepository,
        token_service: TokenService
    ):
        self.user_repo = user_repo
        self.token_service = token_service

    async def execute(self, token: str) -> User:
        """Get current user from access token.

        Args:
            token: JWT access token

        Returns:
            Current authenticated user

        Raises:
            InvalidCredentialsError: If token is invalid
            UserNotFoundError: If user no longer exists
            InactiveUserError: If user account is inactive
        """
        # Verify and decode token
        token_data = self.token_service.verify_token(token)
        if not token_data:
            raise InvalidCredentialsError()

        # Extract email from token
        email = token_data.get("sub")
        if not email:
            raise InvalidCredentialsError()

        # Find user
        user = await self.user_repo.find_by_email(email)
        if not user:
            raise UserNotFoundError(email)

        # Check if user is active
        if not user.is_active:
            raise InactiveUserError(email)

        return user
