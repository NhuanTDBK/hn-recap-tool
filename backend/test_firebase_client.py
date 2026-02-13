#!/usr/bin/env python3
"""Test script for Firebase HN API client."""

import asyncio

from app.infrastructure.services.firebase_hn_client import FirebaseHNClient


async def test_firebase_client():
    """Test Firebase HN client functionality."""
    client = FirebaseHNClient(timeout=10)

    print("=" * 60)
    print("Testing Firebase HackerNews API Client")
    print("=" * 60)

    # Test 1: Get max item ID
    print("\n1. Getting max item ID...")
    max_id = await client.get_max_item_id()
    if max_id:
        print(f"   ✓ Current max item ID: {max_id}")
    else:
        print("   ✗ Failed to get max item ID")
        return

    # Test 2: Fetch a specific item
    print(f"\n2. Fetching item {max_id}...")
    item = await client.fetch_item(max_id)
    if item:
        print(f"   ✓ Item type: {item.get('type')}")
        if item.get('title'):
            print(f"   ✓ Title: {item.get('title')[:60]}...")
    else:
        print("   ✗ Failed to fetch item")

    # Test 3: Fetch front page stories
    print("\n3. Fetching top 5 front page stories...")
    stories = await client.fetch_front_page(limit=5)
    if stories:
        print(f"   ✓ Fetched {len(stories)} stories")
        for i, story in enumerate(stories[:3], 1):
            title = story.get("title", "No title")
            score = story.get("score", 0)
            print(f"   {i}. [{score} pts] {title[:50]}...")
    else:
        print("   ✗ Failed to fetch stories")

    # Test 4: Incremental scanning (last 20 items)
    print(f"\n4. Testing incremental scan (last 20 items from {max_id - 20})...")
    last_id = max_id - 20
    new_items = await client.fetch_new_items(
        last_id=last_id, score_threshold=50, max_items=20
    )
    if new_items:
        print(f"   ✓ Found {len(new_items)} stories with score >= 50")
        for item in new_items[:3]:
            transformed = client.transform_item_to_post(item)
            print(
                f"   - [{transformed['points']} pts] {transformed['title'][:50]}..."
            )
    else:
        print("   ℹ No high-scoring stories in this range")

    # Test 5: Transform item to post format
    print("\n5. Testing item transformation...")
    if stories:
        transformed = client.transform_item_to_post(stories[0])
        print(f"   ✓ Transformed fields:")
        print(f"     - hn_id: {transformed['hn_id']}")
        print(f"     - title: {transformed['title'][:50]}...")
        print(f"     - author: {transformed['author']}")
        print(f"     - points: {transformed['points']}")
        print(f"     - post_type: {transformed['post_type']}")
        print(f"     - domain: {transformed['domain']}")

    print("\n" + "=" * 60)
    print("✅ Firebase client tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_firebase_client())
