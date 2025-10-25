"""Digest API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Annotated, Optional

from app.domain.entities import User
from app.domain.exceptions import DigestNotFoundError, PostNotFoundError
from app.presentation.schemas.digest import (
    DigestResponse,
    DigestListResponse,
    DigestListItem,
    PostResponse,
    PostDetailResponse
)
from app.presentation.api.dependencies import (
    get_current_user,
    get_digest_by_date_use_case,
    get_list_digests_use_case,
    get_post_detail_use_case,
    get_latest_digest_use_case
)
from app.application.use_cases.digests import (
    GetDigestByDateUseCase,
    ListDigestsUseCase,
    GetPostDetailUseCase,
    GetLatestDigestUseCase
)

router = APIRouter(prefix="/api/digests", tags=["Digests"])


@router.get("/latest", response_model=DigestResponse)
async def get_latest_digest(
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[GetLatestDigestUseCase, Depends(get_latest_digest_use_case)]
):
    """Get the most recent digest available.

    Args:
        current_user: Current authenticated user (injected)
        use_case: Get latest digest use case (injected)

    Returns:
        Latest digest

    Raises:
        HTTP 404: If no digests exist
    """
    try:
        digest = await use_case.execute()

        # Convert posts to response schema
        posts = [
            PostResponse(
                id=p.id,
                hn_id=p.hn_id,
                title=p.title,
                author=p.author,
                points=p.points,
                num_comments=p.num_comments,
                created_at=p.created_at,
                url=p.url,
                post_type=p.post_type,
                content=p.content
            )
            for p in digest.posts
        ]

        return DigestResponse(
            id=digest.id,
            date=digest.date,
            total_posts=digest.total_posts,
            created_at=digest.created_at,
            posts=posts
        )
    except DigestNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{date}", response_model=DigestResponse)
async def get_digest_by_date(
    date: str,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[GetDigestByDateUseCase, Depends(get_digest_by_date_use_case)]
):
    """Get digest for a specific date.

    Args:
        date: Date in YYYY-MM-DD format
        current_user: Current authenticated user (injected)
        use_case: Get digest by date use case (injected)

    Returns:
        Digest for the specified date

    Raises:
        HTTP 404: If digest not found for that date
    """
    try:
        digest = await use_case.execute(date)

        # Convert posts to response schema
        posts = [
            PostResponse(
                id=p.id,
                hn_id=p.hn_id,
                title=p.title,
                author=p.author,
                points=p.points,
                num_comments=p.num_comments,
                created_at=p.created_at,
                url=p.url,
                post_type=p.post_type,
                content=p.content
            )
            for p in digest.posts
        ]

        return DigestResponse(
            id=digest.id,
            date=digest.date,
            total_posts=digest.total_posts,
            created_at=digest.created_at,
            posts=posts
        )
    except DigestNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/", response_model=DigestListResponse)
async def list_digests(
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[ListDigestsUseCase, Depends(get_list_digests_use_case)],
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(30, ge=1, le=100, description="Max number of digests")
):
    """List digests within a date range.

    Args:
        current_user: Current authenticated user (injected)
        use_case: List digests use case (injected)
        start_date: Start date (optional, defaults to 30 days ago)
        end_date: End date (optional, defaults to today)
        limit: Maximum number of digests (1-100, default 30)

    Returns:
        List of digests (summary only, no posts)
    """
    digests = await use_case.execute(
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )

    # Convert to response schema (summary only)
    digest_items = [
        DigestListItem(
            id=d.id,
            date=d.date,
            total_posts=d.total_posts,
            created_at=d.created_at
        )
        for d in digests
    ]

    return DigestListResponse(
        digests=digest_items,
        total=len(digest_items)
    )


@router.get("/posts/{post_id}", response_model=PostDetailResponse)
async def get_post_detail(
    post_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[GetPostDetailUseCase, Depends(get_post_detail_use_case)]
):
    """Get full details for a specific post.

    Args:
        post_id: Post's unique identifier
        current_user: Current authenticated user (injected)
        use_case: Get post detail use case (injected)

    Returns:
        Post with full content

    Raises:
        HTTP 404: If post not found
    """
    try:
        post = await use_case.execute(post_id)

        return PostDetailResponse(
            id=post.id,
            hn_id=post.hn_id,
            title=post.title,
            author=post.author,
            points=post.points,
            num_comments=post.num_comments,
            created_at=post.created_at,
            url=post.url,
            post_type=post.post_type,
            content=post.content,
            raw_content=post.raw_content,
            collected_at=post.collected_at
        )
    except PostNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
