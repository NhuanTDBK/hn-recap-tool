"""JWT token service implementation."""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import logging

from app.application.interfaces import TokenService
from app.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class JWTTokenService(TokenService):
    """JWT token service using python-jose."""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: Optional[str] = None,
        expire_minutes: Optional[int] = None
    ):
        """Initialize JWT token service.

        Args:
            secret_key: Secret key for signing tokens (defaults to settings)
            algorithm: Algorithm to use (defaults to settings)
            expire_minutes: Token expiration in minutes (defaults to settings)
        """
        self.secret_key = secret_key or settings.secret_key
        self.algorithm = algorithm or settings.algorithm
        self.expire_minutes = expire_minutes or settings.access_token_expire_minutes

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[int] = None
    ) -> str:
        """Create a JWT access token.

        Args:
            data: Data to encode in token
            expires_delta: Token expiration time in minutes (overrides default)

        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()

        # Set expiration
        expire_minutes = expires_delta or self.expire_minutes
        expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
        to_encode.update({"exp": expire})

        # Encode token
        encoded_jwt = jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.algorithm
        )

        return encoded_jwt

    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode a JWT token.

        Args:
            token: JWT token to verify

        Returns:
            Decoded token data if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
