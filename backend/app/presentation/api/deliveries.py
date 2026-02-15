"""Delivery API endpoints for managing Telegram digest delivery."""

import logging
from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.presentation.schemas.delivery import (
    DeliveryPipelineRequest,
    DeliveryPipelineResponse,
)
from app.application.use_cases.delivery_pipeline import DeliveryPipeline
from app.infrastructure.database.base import get_session
from app.infrastructure.repositories.postgres.delivery_repo import (
    PostgresDeliveryRepository,
)
from app.presentation.bot.handlers.delivery import DigestDeliveryHandler
from app.presentation.bot import get_bot_manager
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deliveries", tags=["Deliveries"])


async def get_delivery_pipeline(
    session: Annotated[AsyncSession, Depends(get_session)]
) -> DeliveryPipeline:
    """Get delivery pipeline instance with dependencies injected.

    Args:
        session: Async database session

    Returns:
        DeliveryPipeline instance
    """
    delivery_repo = PostgresDeliveryRepository(session)
    bot_manager = get_bot_manager()
    delivery_handler = DigestDeliveryHandler(bot_manager)

    return DeliveryPipeline(
        db_session=session,
        delivery_repo=delivery_repo,
        delivery_handler=delivery_handler,
    )


@router.post("/run", response_model=DeliveryPipelineResponse, status_code=200)
async def run_delivery_pipeline(
    request: DeliveryPipelineRequest,
    pipeline: Annotated[DeliveryPipeline, Depends(get_delivery_pipeline)],
):
    """Execute the delivery pipeline to send digests to all active users.

    This endpoint orchestrates the entire delivery workflow:
    1. Selects posts for each active user based on their last_delivered_at
    2. Formats messages per user's delivery style
    3. Sends Telegram messages via the bot
    4. Tracks deliveries in the database
    5. Updates user.last_delivered_at

    Query Parameters:
        - batch_id: Optional batch identifier (generated if not provided)
        - max_posts_per_user: Max posts per user (1-100, default 10)
        - skip_user_ids: User IDs to skip (optional)
        - dry_run: If True, simulate without actual sends (default False)

    Returns:
        DeliveryPipelineResponse with execution statistics

    Raises:
        HTTP 500: If fatal error occurs during pipeline execution
    """
    try:
        logger.info(
            f"Delivery pipeline request: batch_id={request.batch_id}, "
            f"max_posts={request.max_posts_per_user}, "
            f"dry_run={request.dry_run}"
        )

        # Execute pipeline
        stats = await pipeline.run(
            batch_id=request.batch_id,
            max_posts_per_user=request.max_posts_per_user,
            skip_user_ids=request.skip_user_ids,
            dry_run=request.dry_run,
        )

        # Convert error items if they exist
        errors = []
        if stats.get("errors"):
            for error in stats["errors"]:
                errors.append(error)

        logger.info(
            f"Delivery pipeline completed: batch_id={stats['batch_id']}, "
            f"delivered={stats['users_delivered']}, "
            f"messages={stats['total_messages_sent']}"
        )

        return DeliveryPipelineResponse(
            batch_id=stats["batch_id"],
            total_users=stats["total_users"],
            users_delivered=stats["users_delivered"],
            users_skipped=stats["users_skipped"],
            total_messages_sent=stats["total_messages_sent"],
            total_posts_delivered=stats["total_posts_delivered"],
            errors=errors,
            start_time=stats["start_time"],
            end_time=stats["end_time"],
            duration_seconds=stats["duration_seconds"],
        )

    except Exception as e:
        logger.error(f"Fatal error in delivery pipeline endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Delivery pipeline failed: {str(e)[:100]}",
        )


@router.post("/dry-run", response_model=DeliveryPipelineResponse, status_code=200)
async def run_dry_run_delivery(
    request: DeliveryPipelineRequest,
    pipeline: Annotated[DeliveryPipeline, Depends(get_delivery_pipeline)],
):
    """Execute a dry-run of the delivery pipeline.

    Simulates the entire workflow without actually sending messages or
    updating the database. Useful for testing and debugging.

    Returns:
        DeliveryPipelineResponse with what would have been executed
    """
    try:
        logger.info(
            f"Dry-run delivery pipeline: batch_id={request.batch_id}, "
            f"max_posts={request.max_posts_per_user}"
        )

        # Force dry_run=True
        stats = await pipeline.run(
            batch_id=request.batch_id,
            max_posts_per_user=request.max_posts_per_user,
            skip_user_ids=request.skip_user_ids,
            dry_run=True,
        )

        errors = []
        if stats.get("errors"):
            for error in stats["errors"]:
                errors.append(error)

        logger.info(
            f"Dry-run completed: batch_id={stats['batch_id']}, "
            f"would_deliver={stats['users_delivered']}, "
            f"would_send={stats['total_messages_sent']}"
        )

        return DeliveryPipelineResponse(
            batch_id=stats["batch_id"],
            total_users=stats["total_users"],
            users_delivered=stats["users_delivered"],
            users_skipped=stats["users_skipped"],
            total_messages_sent=stats["total_messages_sent"],
            total_posts_delivered=stats["total_posts_delivered"],
            errors=errors,
            start_time=stats["start_time"],
            end_time=stats["end_time"],
            duration_seconds=stats["duration_seconds"],
        )

    except Exception as e:
        logger.error(f"Fatal error in dry-run delivery pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dry-run failed: {str(e)[:100]}",
        )
