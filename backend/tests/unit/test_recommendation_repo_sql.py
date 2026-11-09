"""Checks the candidate query's SQL, since no test database is available here.

These compile the statement for PostgreSQL and look for the filters that matter. They
do not replace running it against a real database (see the dry run in the plan).
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.dialects import postgresql

from app.infrastructure.repositories.postgres.recommendation_repo import (
    PostgresRecommendationRepository,
)


@pytest.fixture(scope="module")
def sql() -> str:
    stmt = PostgresRecommendationRepository(None).candidates_query(
        7, datetime.now(timezone.utc), 150
    )
    return str(stmt.compile(dialect=postgresql.dialect()))


def test_only_this_feeds_summaries_are_joined(sql):
    assert "summaries.user_id =" in sql and "summaries.created_at >=" in sql


def test_only_live_crawled_stories(sql):
    for fragment in (
        "posts.type =",
        "posts.is_dead IS false",
        "posts.is_deleted IS false",
        "posts.is_crawl_success IS true",
    ):
        assert fragment in sql


def test_video_posts_and_untitled_posts_are_excluded(sql):
    assert "posts.title NOT ILIKE" in sql and "posts.title IS NOT NULL" in sql


def test_saved_rejected_and_already_recommended_posts_are_excluded(sql):
    assert "posts.id NOT IN (SELECT user_activity_log.post_id" in sql
    assert "posts.id NOT IN (SELECT recommendations.post_id" in sql


def test_highest_score_first(sql):
    assert "ORDER BY posts.score DESC" in sql
