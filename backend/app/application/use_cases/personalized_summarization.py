"""Personalized summarization pipeline with grouping by delivery_style.

This module implements personalized summarization that:
1. Groups users by delivery_style to minimize API calls
2. Uses incremental time windows to process only new posts
3. Generates per-user summaries with user_id
4. Leverages prompt caching for efficiency
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Post, Summary, User
from app.infrastructure.storage.rocksdb_store import RocksDBContentStore

logger = logging.getLogger(__name__)


# Deprecated: Old delivery_style mapping (kept for backward compatibility)
STYLE_TO_PROMPT_TYPE = {
    "flat_scroll": "basic",      # Detailed summaries for comprehensive view
    "brief": "concise",           # Ultra-brief summaries for quick scanning
}


def get_prompt_type_for_user(user: User) -> str:
    """Get prompt type based on user's summary preferences.

    Args:
        user: User object with summary_preferences

    Returns:
        Prompt type string (basic, technical, business, concise, personalized)
    """
    # Use new summary_preferences if available
    if user.summary_preferences and isinstance(user.summary_preferences, dict):
        style = user.summary_preferences.get("style", "basic")
        # Validate style is one of the supported types
        valid_styles = ["basic", "technical", "business", "concise", "personalized"]
        if style in valid_styles:
            return style

    # Fallback to old delivery_style mapping for backward compatibility
    return STYLE_TO_PROMPT_TYPE.get(user.delivery_style, "basic")


async def get_user_last_summary_time(
    session: AsyncSession,
    user_id: int,
    default_hours: int = 6
) -> datetime:
    """Get user's most recent summary timestamp.

    Args:
        session: Database session
        user_id: User ID
        default_hours: Default lookback window if no summaries exist

    Returns:
        Latest summary created_at, or NOW - default_hours
    """
    stmt = select(func.max(Summary.created_at)).where(
        Summary.user_id == user_id
    )
    result = await session.execute(stmt)
    last_time = result.scalar_one_or_none()

    if last_time is None:
        return datetime.now(timezone.utc) - timedelta(hours=default_hours)

    return last_time


async def get_group_time_window(
    session: AsyncSession,
    users: List[User],
    default_hours: int = 6
) -> datetime:
    """Get earliest last summary time across all users in group.

    This ensures we fetch enough posts to satisfy all users in the group.

    Args:
        session: Database session
        users: List of users in the group
        default_hours: Default lookback window

    Returns:
        Earliest time across all users
    """
    times = []
    for user in users:
        last_time = await get_user_last_summary_time(session, user.id, default_hours)
        times.append(last_time)

    earliest = min(times) if times else datetime.now(timezone.utc) - timedelta(hours=default_hours)

    logger.info(
        f"Group time window: {earliest.isoformat()} "
        f"(earliest of {len(users)} users, covers {(datetime.now(timezone.utc) - earliest).total_seconds() / 3600:.1f}h)"
    )

    return earliest


async def find_posts_in_time_window(
    session: AsyncSession,
    since: datetime,
    limit: Optional[int] = None,
    fallback_to_latest: bool = True,
    latest_post_limit: int = 10
) -> List[Post]:
    """Find posts created after the given time.

    Args:
        session: Database session
        since: Fetch posts created after this time
        limit: Maximum posts to return
        fallback_to_latest: If no posts in time window, get latest N posts
        latest_post_limit: Number of latest posts to return on fallback

    Returns:
        List of posts
    """
    stmt = select(Post).where(
        and_(
            Post.created_at >= since,
            Post.type == "story",
            Post.is_dead.is_(False),
            Post.is_deleted.is_(False),
            Post.is_crawl_success.is_(True),
        )
    ).order_by(Post.score.desc())

    if limit:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    posts = list(result.scalars().all())

    if not posts and fallback_to_latest:
        logger.info(
            f"No posts found in time window (since {since.isoformat()}), "
            f"falling back to latest {latest_post_limit} posts"
        )

        # Get latest posts regardless of time
        stmt = select(Post).where(
            and_(
                Post.type == "story",
                Post.is_dead.is_(False),
                Post.is_deleted.is_(False),
                Post.is_crawl_success.is_(True),
            )
        ).order_by(Post.created_at.desc()).limit(latest_post_limit)

        result = await session.execute(stmt)
        posts = list(result.scalars().all())

        logger.info(f"Found {len(posts)} latest posts (fallback mode)")
    else:
        logger.info(
            f"Found {len(posts)} posts in time window "
            f"(since {since.isoformat()})"
        )

    return posts


async def filter_posts_for_user(
    session: AsyncSession,
    user: User,
    posts: List[Post],
    prompt_type: str
) -> List[Post]:
    """Filter posts that user doesn't already have summaries for.

    Args:
        session: Database session
        user: User to check
        posts: Posts to filter
        prompt_type: Prompt type to check

    Returns:
        Posts without summaries for this user/prompt_type
    """
    if not posts:
        return []

    post_ids = [p.id for p in posts]

    # Find existing summaries
    stmt = select(Summary.post_id).where(
        and_(
            Summary.user_id == user.id,
            Summary.post_id.in_(post_ids),
            Summary.prompt_type == prompt_type
        )
    )

    result = await session.execute(stmt)
    existing_post_ids = set(result.scalars().all())

    # Filter to posts without summaries
    filtered = [p for p in posts if p.id not in existing_post_ids]

    logger.debug(
        f"User {user.id}: {len(filtered)} new posts "
        f"(filtered from {len(posts)})"
    )

    return filtered


async def get_post_content(
    post: Post,
    content_store: RocksDBContentStore
) -> str:
    """Get post content from RocksDB or construct from metadata.

    Args:
        post: Post object
        content_store: RocksDB store

    Returns:
        Markdown content string
    """
    # Try to read from RocksDB
    try:
        if post.has_markdown:
            content = await content_store.get_markdown_content(post.hn_id)
            if content:
                return content
    except Exception as e:
        logger.warning(f"Failed to read markdown for post {post.id}: {e}")

    # Fallback: construct from post fields
    parts = []
    if post.title:
        parts.append(f"# {post.title}")
    if post.url:
        parts.append(f"\n## URL: {post.url}")
    if post.domain:
        parts.append(f"Domain: {post.domain}")

    parts.append(
        f"\n## Metadata\n"
        f"- Score: {post.score}\n"
        f"- Comments: {post.comment_count}\n"
        f"- Author: {post.author}"
    )

    # Try to get text content
    try:
        if post.has_text:
            text_content = await content_store.get_text_content(post.hn_id)
            if text_content:
                parts.append(f"\n## Content\n\n{text_content[:5000]}")
    except Exception as e:
        logger.warning(f"Failed to read text for post {post.id}: {e}")

    return "\n".join(parts)


async def group_users_by_delivery_style(
    session: AsyncSession,
    user_ids: Optional[List[int]] = None
) -> Dict[str, List[User]]:
    """Group users by their summary_preferences.style.

    Note: Function name kept for backward compatibility but now groups by
    summary_preferences.style instead of delivery_style.

    Args:
        session: Database session
        user_ids: Optional list of specific user IDs to process

    Returns:
        Dict mapping prompt_type to list of users
    """
    stmt = select(User).where(User.status == "active")

    if user_ids:
        stmt = stmt.where(User.id.in_(user_ids))

    result = await session.execute(stmt)
    users = list(result.scalars().all())

    # Group by prompt_type (from summary_preferences.style)
    groups: Dict[str, List[User]] = {}
    for user in users:
        prompt_type = get_prompt_type_for_user(user)
        if prompt_type not in groups:
            groups[prompt_type] = []
        groups[prompt_type].append(user)

    # Sort users by ID within each group (deterministic)
    for prompt_type in groups:
        groups[prompt_type].sort(key=lambda u: u.id)

    logger.info(
        f"Grouped {len(users)} users into {len(groups)} summary styles: "
        f"{', '.join([f'{style}({len(grp)})' for style, grp in groups.items()])}"
    )

    return groups


async def summarize_for_users_in_group(
    session: AsyncSession,
    content_store: RocksDBContentStore,
    users: List[User],
    posts: List[Post],
    prompt_type: str,
    openai_client,
    agent_instructions: str,
    model: str = "gpt-4o-mini"
) -> Dict:
    """Generate summaries for all users in a group.

    This is the core of the grouped summarization approach. We:
    1. Summarize each post once (with caching benefits)
    2. Distribute the summary to all users in the group
    3. Only store summaries for posts each user needs

    Args:
        session: Database session
        content_store: RocksDB store
        users: Users in this group
        posts: Posts to summarize
        prompt_type: Prompt type for this group
        openai_client: OpenAI client instance
        agent_instructions: Cached agent instructions
        model: OpenAI model to use

    Returns:
        Statistics dict
    """
    stats = {
        "total_posts": len(posts),
        "total_users": len(users),
        "summaries_created": 0,
        "posts_summarized": 0,
        "failed": 0,
        "skipped": 0,
        "total_tokens": 0,
        "total_cost": Decimal("0"),
        "api_calls": 0,
    }

    for post in posts:
        try:
            # Get content
            content = await get_post_content(post, content_store)

            if not content.strip():
                logger.warning(f"Post {post.id} has no content, skipping")
                stats["skipped"] += 1
                continue

            # Call OpenAI API once for this post (with prompt caching)
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": agent_instructions,
                        "cache_control": {"type": "ephemeral"}
                    },
                    {"role": "user", "content": content}
                ],
                temperature=0.3,
                max_tokens=500
            )

            summary_text = response.choices[0].message.content.strip()
            stats["api_calls"] += 1
            stats["posts_summarized"] += 1

            # Calculate cost (accounting for caching)
            if response.usage:
                actual_tokens = response.usage.total_tokens
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens

                # Check for cached tokens
                cached_tokens = 0
                if hasattr(response.usage, 'prompt_tokens_details'):
                    details = response.usage.prompt_tokens_details
                    if hasattr(details, 'cached_tokens') and details.cached_tokens:
                        cached_tokens = details.cached_tokens

                # Calculate cost with caching discount
                uncached_prompt_tokens = prompt_tokens - cached_tokens
                input_cost = (uncached_prompt_tokens * 0.15 / 1_000_000) + (cached_tokens * 0.015 / 1_000_000)
                output_cost = completion_tokens * 0.60 / 1_000_000
                cost_per_summary = Decimal(str(input_cost + output_cost))

                if cached_tokens > 0:
                    logger.debug(f"Cache hit: {cached_tokens} tokens (saved ~${(cached_tokens * 0.135 / 1_000_000):.6f})")
            else:
                actual_tokens = len(content) // 4 + len(summary_text) // 4
                cost_per_summary = Decimal(str(actual_tokens * 0.00000015))

            # Distribute summary to all users in group who need it
            for user in users:
                # Check if user already has this summary
                existing = await session.execute(
                    select(Summary).where(
                        and_(
                            Summary.user_id == user.id,
                            Summary.post_id == post.id,
                            Summary.prompt_type == prompt_type
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    continue  # User already has this summary

                # Create summary record for this user
                summary = Summary(
                    post_id=post.id,
                    user_id=user.id,  # Personalized to this user
                    prompt_type=prompt_type,
                    summary_text=summary_text,
                    key_points=[],
                    technical_level="intermediate",
                    token_count=actual_tokens,
                    cost_usd=cost_per_summary,
                )

                session.add(summary)
                stats["summaries_created"] += 1

            # Commit after each post to avoid losing work
            await session.commit()

            stats["total_tokens"] += actual_tokens
            stats["total_cost"] += cost_per_summary

            logger.debug(
                f"✓ Post {post.id}: summarized and distributed to {len(users)} users"
            )

        except Exception as e:
            logger.error(f"Failed to summarize post {post.id}: {e}")
            stats["failed"] += 1
            await session.rollback()
            continue

    return stats


async def run_personalized_summarization(
    session: AsyncSession,
    content_store: RocksDBContentStore,
    openai_client,
    user_ids: Optional[List[int]] = None,
    default_hours: int = 6,
    post_limit: Optional[int] = None,
    dry_run: bool = False
) -> Dict:
    """Run personalized summarization pipeline with grouping by delivery_style.

    Args:
        session: Database session
        content_store: RocksDB store
        openai_client: OpenAI client instance
        user_ids: Optional list of user IDs to process (None = all active users)
        default_hours: Default lookback window for users without summaries
        post_limit: Maximum posts to process per group
        dry_run: If True, don't actually create summaries

    Returns:
        Statistics dict
    """
    from app.infrastructure.agents.summarization_agent import create_summarization_agent
    from app.infrastructure.config.settings import settings

    logger.info("="*80)
    logger.info("PERSONALIZED SUMMARIZATION PIPELINE")
    logger.info("="*80)

    overall_stats = {
        "total_users": 0,
        "total_groups": 0,
        "total_posts_processed": 0,
        "total_summaries_created": 0,
        "total_api_calls": 0,
        "total_tokens": 0,
        "total_cost": Decimal("0"),
        "groups": {},
    }

    # Step 1: Group users by delivery_style
    groups = await group_users_by_delivery_style(session, user_ids)
    overall_stats["total_groups"] = len(groups)
    overall_stats["total_users"] = sum(len(users) for users in groups.values())

    if not groups:
        logger.info("No active users to process")
        return overall_stats

    # Step 2: Process each group
    for prompt_type, users in groups.items():
        # Note: groups are now keyed by prompt_type directly from summary_preferences

        logger.info(f"\n{'='*80}")
        logger.info(f"Processing group: {prompt_type} ({len(users)} users)")
        logger.info(f"{'='*80}")

        # Create agent for this group (with caching)
        agent = create_summarization_agent(
            prompt_type=prompt_type,
            use_structured_output=False
        )

        # Get group time window
        since = await get_group_time_window(session, users, default_hours)

        # Find posts in time window
        posts = await find_posts_in_time_window(session, since, post_limit)

        if not posts:
            logger.info(f"No posts found for group {prompt_type}")
            overall_stats["groups"][prompt_type] = {
                "users": len(users),
                "posts": 0,
                "summaries": 0,
            }
            continue

        if dry_run:
            logger.info(f"DRY RUN: Would process {len(posts)} posts for {len(users)} users")
            overall_stats["groups"][prompt_type] = {
                "users": len(users),
                "posts": len(posts),
                "summaries": len(posts) * len(users),
            }
            continue

        # Summarize posts for all users in group
        group_stats = await summarize_for_users_in_group(
            session,
            content_store,
            users,
            posts,
            prompt_type,
            openai_client,
            agent.instructions,
            settings.openai_model
        )

        # Update overall stats
        overall_stats["total_posts_processed"] += group_stats["posts_summarized"]
        overall_stats["total_summaries_created"] += group_stats["summaries_created"]
        overall_stats["total_api_calls"] += group_stats["api_calls"]
        overall_stats["total_tokens"] += group_stats["total_tokens"]
        overall_stats["total_cost"] += group_stats["total_cost"]

        overall_stats["groups"][prompt_type] = {
            "users": len(users),
            "posts": group_stats["posts_summarized"],
            "summaries": group_stats["summaries_created"],
            "tokens": group_stats["total_tokens"],
            "cost": float(group_stats["total_cost"]),
        }

        logger.info(
            f"Group {prompt_type} complete: "
            f"{group_stats['summaries_created']} summaries created "
            f"from {group_stats['posts_summarized']} posts "
            f"via {group_stats['api_calls']} API calls"
        )

    # Step 3: Print summary
    logger.info(f"\n{'='*80}")
    logger.info("RESULTS")
    logger.info(f"{'='*80}")
    logger.info(f"Total users: {overall_stats['total_users']}")
    logger.info(f"Total groups: {overall_stats['total_groups']}")
    logger.info(f"Posts processed: {overall_stats['total_posts_processed']}")
    logger.info(f"Summaries created: {overall_stats['total_summaries_created']}")
    logger.info(f"API calls: {overall_stats['total_api_calls']}")

    if not dry_run:
        logger.info(f"Total tokens: {overall_stats['total_tokens']}")
        logger.info(f"Total cost: ${float(overall_stats['total_cost']):.4f}")

        if overall_stats['total_api_calls'] > 0:
            avg_tokens = overall_stats['total_tokens'] / overall_stats['total_api_calls']
            logger.info(f"Avg tokens per API call: {avg_tokens:.0f}")

        # Calculate efficiency gain
        naive_api_calls = overall_stats['total_summaries_created']
        actual_api_calls = overall_stats['total_api_calls']
        if naive_api_calls > 0:
            reduction_pct = (1 - actual_api_calls / naive_api_calls) * 100
            logger.info(f"Efficiency: {reduction_pct:.1f}% fewer API calls vs naive approach")

    logger.info(f"{'='*80}\n")

    return overall_stats
