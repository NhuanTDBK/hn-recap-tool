"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated

from app.domain.entities import User
from app.domain.exceptions import UserAlreadyExistsError, InvalidCredentialsError
from app.presentation.schemas.user import (
    UserCreate,
    UserResponse,
    LoginRequest,
    Token
)
from app.presentation.api.dependencies import (
    get_register_user_use_case,
    get_login_user_use_case,
    get_current_user
)
from app.application.use_cases.auth import RegisterUserUseCase, LoginUserUseCase

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    use_case: Annotated[RegisterUserUseCase, Depends(get_register_user_use_case)]
):
    """Register a new user.

    Args:
        user_data: User registration data (email and password)
        use_case: Register user use case (injected)

    Returns:
        Created user data (excluding password)

    Raises:
        HTTP 400: If user already exists
    """
    try:
        user = await use_case.execute(user_data.email, user_data.password)
        return UserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at,
            is_active=user.is_active
        )
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    use_case: Annotated[LoginUserUseCase, Depends(get_login_user_use_case)]
):
    """Authenticate user and get access token.

    Args:
        login_data: Login credentials (email and password)
        use_case: Login user use case (injected)

    Returns:
        JWT access token

    Raises:
        HTTP 401: If credentials are invalid
    """
    try:
        user, access_token = await use_case.execute(
            login_data.email,
            login_data.password
        )
        return Token(access_token=access_token, token_type="bearer")
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Get current authenticated user information.

    Args:
        current_user: Current user (injected from token)

    Returns:
        Current user data

    Raises:
        HTTP 401: If token is invalid
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at,
        is_active=current_user.is_active
    )
