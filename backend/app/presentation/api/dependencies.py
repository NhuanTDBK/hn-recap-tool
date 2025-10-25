"""FastAPI dependency injection for use cases and services."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated

from app.domain.entities import User
from app.application.interfaces import (
    UserRepository,
    PostRepository,
    DigestRepository,
    PasswordHasher,
    TokenService,
    CacheService,
    HNService,
    ContentExtractor
)
from app.application.use_cases.auth import (
    RegisterUserUseCase,
    LoginUserUseCase,
    GetCurrentUserUseCase
)
from app.application.use_cases.digests import (
    GetDigestByDateUseCase,
    ListDigestsUseCase,
    GetPostDetailUseCase,
    GetLatestDigestUseCase
)
from app.application.use_cases.collection import (
    CollectPostsUseCase,
    ExtractContentUseCase,
    CreateDigestUseCase
)
from app.infrastructure.repositories.jsonl_user_repo import JSONLUserRepository
from app.infrastructure.repositories.jsonl_post_repo import JSONLPostRepository
from app.infrastructure.repositories.jsonl_digest_repo import JSONLDigestRepository
from app.infrastructure.security.password_hasher import BcryptPasswordHasher
from app.infrastructure.security.jwt_handler import JWTTokenService
from app.infrastructure.services.redis_cache import RedisCacheService
from app.infrastructure.services.hn_client import AlgoliaHNClient
from app.infrastructure.services.content_extractor import TrafilaturaContentExtractor
from app.infrastructure.config.settings import settings

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# Repository Dependencies

def get_user_repository() -> UserRepository:
    """Get user repository instance."""
    file_path = f"{settings.data_dir}/{settings.user_data_file}"
    return JSONLUserRepository(file_path)


def get_post_repository() -> PostRepository:
    """Get post repository instance."""
    return JSONLPostRepository(settings.data_dir)


def get_digest_repository() -> DigestRepository:
    """Get digest repository instance."""
    return JSONLDigestRepository(settings.data_dir)


# Service Dependencies

def get_password_hasher() -> PasswordHasher:
    """Get password hasher instance."""
    return BcryptPasswordHasher()


def get_token_service() -> TokenService:
    """Get JWT token service instance."""
    return JWTTokenService()


def get_cache_service() -> CacheService:
    """Get Redis cache service instance."""
    return RedisCacheService()


def get_hn_service() -> HNService:
    """Get HackerNews API client instance."""
    return AlgoliaHNClient()


def get_content_extractor() -> ContentExtractor:
    """Get content extractor instance."""
    return TrafilaturaContentExtractor()


# Auth Use Case Dependencies

def get_register_user_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    password_hasher: Annotated[PasswordHasher, Depends(get_password_hasher)]
) -> RegisterUserUseCase:
    """Get register user use case."""
    return RegisterUserUseCase(user_repo, password_hasher)


def get_login_user_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    password_hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    token_service: Annotated[TokenService, Depends(get_token_service)]
) -> LoginUserUseCase:
    """Get login user use case."""
    return LoginUserUseCase(user_repo, password_hasher, token_service)


def get_current_user_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    token_service: Annotated[TokenService, Depends(get_token_service)]
) -> GetCurrentUserUseCase:
    """Get current user use case."""
    return GetCurrentUserUseCase(user_repo, token_service)


# Current User Dependency (for protected routes)

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    use_case: Annotated[GetCurrentUserUseCase, Depends(get_current_user_use_case)]
) -> User:
    """Get current authenticated user from token.

    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        user = await use_case.execute(token)
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Digest Use Case Dependencies

def get_digest_by_date_use_case(
    digest_repo: Annotated[DigestRepository, Depends(get_digest_repository)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)]
) -> GetDigestByDateUseCase:
    """Get digest by date use case."""
    return GetDigestByDateUseCase(digest_repo, cache_service)


def get_list_digests_use_case(
    digest_repo: Annotated[DigestRepository, Depends(get_digest_repository)]
) -> ListDigestsUseCase:
    """Get list digests use case."""
    return ListDigestsUseCase(digest_repo)


def get_post_detail_use_case(
    post_repo: Annotated[PostRepository, Depends(get_post_repository)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)]
) -> GetPostDetailUseCase:
    """Get post detail use case."""
    return GetPostDetailUseCase(post_repo, cache_service)


def get_latest_digest_use_case(
    digest_repo: Annotated[DigestRepository, Depends(get_digest_repository)]
) -> GetLatestDigestUseCase:
    """Get latest digest use case."""
    return GetLatestDigestUseCase(digest_repo)


# Collection Use Case Dependencies

def get_collect_posts_use_case(
    post_repo: Annotated[PostRepository, Depends(get_post_repository)],
    hn_service: Annotated[HNService, Depends(get_hn_service)]
) -> CollectPostsUseCase:
    """Get collect posts use case."""
    return CollectPostsUseCase(post_repo, hn_service)


def get_extract_content_use_case(
    post_repo: Annotated[PostRepository, Depends(get_post_repository)],
    content_extractor: Annotated[ContentExtractor, Depends(get_content_extractor)]
) -> ExtractContentUseCase:
    """Get extract content use case."""
    return ExtractContentUseCase(post_repo, content_extractor)


def get_create_digest_use_case(
    digest_repo: Annotated[DigestRepository, Depends(get_digest_repository)],
    post_repo: Annotated[PostRepository, Depends(get_post_repository)]
) -> CreateDigestUseCase:
    """Get create digest use case."""
    return CreateDigestUseCase(digest_repo, post_repo)
