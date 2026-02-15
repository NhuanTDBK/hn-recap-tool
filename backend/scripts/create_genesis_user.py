#!/usr/bin/env python
"""Create genesis user (id=0) with detail-summary preference for testing.

This script:
1. Creates genesis user with id=0, telegram_id=0
2. Sets preference to detail-summary
3. Verifies user creation
4. Shows user details for testing
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database.base import Base
from app.infrastructure.database.models import User

# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://hn_pal:hn_pal_dev@localhost:5433/hn_pal"
)


async def create_genesis_user():
    """Create genesis user for testing delivery system."""

    # Create async engine
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
    )

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Check if genesis user already exists
            from sqlalchemy import select

            stmt = select(User).where(User.id == 0)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"✓ Genesis user already exists:")
                print(f"  ID: {existing_user.id}")
                print(f"  Telegram ID: {existing_user.telegram_id}")
                print(f"  Username: {existing_user.username}")
                print(f"  Interests: {existing_user.interests}")
                print(f"  Status: {existing_user.status}")
                print(f"  Delivery Style: {existing_user.delivery_style}")
                return existing_user

            # Create genesis user
            genesis_user = User(
                id=0,
                telegram_id=0,
                username="genesis",
                interests=["distributed systems", "rust", "databases", "AI"],
                memory_enabled=True,
                status="active",
                delivery_style="detail-summary",
            )

            session.add(genesis_user)
            await session.commit()
            await session.refresh(genesis_user)

            print("✓ Genesis user created successfully!")
            print(f"\nUser Details:")
            print(f"  ID: {genesis_user.id}")
            print(f"  Telegram ID: {genesis_user.telegram_id}")
            print(f"  Username: {genesis_user.username}")
            print(f"  Interests: {genesis_user.interests}")
            print(f"  Memory Enabled: {genesis_user.memory_enabled}")
            print(f"  Status: {genesis_user.status}")
            print(f"  Delivery Style: {genesis_user.delivery_style}")
            print(f"  Last Delivered At: {genesis_user.last_delivered_at}")
            print(f"  Created At: {genesis_user.created_at}")

            return genesis_user

        except Exception as e:
            print(f"✗ Error creating genesis user: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()


async def list_users():
    """List all users in database."""

    # Create async engine
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
    )

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            from sqlalchemy import select

            stmt = select(User).order_by(User.id)
            result = await session.execute(stmt)
            users = result.scalars().all()

            print(f"\n\nAll Users in Database ({len(users)}):")
            print("=" * 80)

            for user in users:
                print(f"\nUser ID {user.id}:")
                print(f"  Telegram ID: {user.telegram_id}")
                print(f"  Username: {user.username}")
                print(f"  Interests: {user.interests}")
                print(f"  Status: {user.status}")
                print(f"  Delivery Style: {user.delivery_style}")
                print(f"  Last Delivered: {user.last_delivered_at}")
                print(f"  Created: {user.created_at}")

        except Exception as e:
            print(f"✗ Error listing users: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("Creating Genesis User for HN Pal Delivery System")
    print("=" * 80)
    print()

    # Create genesis user
    asyncio.run(create_genesis_user())

    # List all users
    asyncio.run(list_users())

    print("\n" + "=" * 80)
    print("✓ Genesis user setup complete!")
