#!/usr/bin/env python3
"""Quick test script to verify database connectivity and models."""

import asyncio
from datetime import datetime

from app.infrastructure.database.base import engine
from app.infrastructure.database.models import Post
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker


async def test_database():
    """Test database connection and basic operations."""
    print("Testing PostgreSQL connection...")

    # Create async session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Test 1: Check if posts table exists
        print("\n1. Querying posts table...")
        stmt = select(Post).limit(5)
        result = await session.execute(stmt)
        posts = result.scalars().all()
        print(f"   ✓ Found {len(posts)} posts in database")

        # Test 2: Create a test post
        print("\n2. Creating test post...")
        test_post = Post(
            hn_id=99999999,
            type="story",
            title="Test Post - PostgreSQL Connection",
            author="test_user",
            url="https://example.com",
            score=100,
            comment_count=50,
            created_at=datetime.utcnow(),
        )
        session.add(test_post)
        await session.commit()
        print(f"   ✓ Test post created with ID: {test_post.id}")

        # Test 3: Query the test post
        print("\n3. Querying test post...")
        stmt = select(Post).where(Post.hn_id == 99999999)
        result = await session.execute(stmt)
        found_post = result.scalar_one_or_none()
        if found_post:
            print(f"   ✓ Test post found: {found_post.title}")

        # Test 4: Update crawl status
        print("\n4. Updating crawl status...")
        found_post.is_crawl_success = True
        found_post.has_html = True
        found_post.has_text = True
        found_post.has_markdown = True
        found_post.content_length = 1234
        await session.commit()
        print("   ✓ Crawl status updated")

        # Test 5: Clean up test post
        print("\n5. Cleaning up test post...")
        await session.delete(found_post)
        await session.commit()
        print("   ✓ Test post deleted")

    print("\n✅ All database tests passed!")
    print("\nDatabase is ready for use.")
    print("  - PostgreSQL: localhost:5433")
    print("  - Database: hn_pal")
    print("  - User: hn_pal")


if __name__ == "__main__":
    asyncio.run(test_database())
