#!/usr/bin/env python3
"""Test RocksDB content retrieval."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infrastructure.storage.rocksdb_store import RocksDBContentStore


async def main():
    """Test content retrieval from RocksDB."""
    store = RocksDBContentStore(db_path="data/content.rocksdb")

    print("=" * 70)
    print("RocksDB Content Retrieval Test")
    print("=" * 70)

    # Get stats
    stats = store.get_stats()
    print(f"\nDatabase Statistics:")
    print(f"  HTML entries:     {stats['html_count']}")
    print(f"  Text entries:     {stats['text_count']}")
    print(f"  Markdown entries: {stats['markdown_count']}")
    print(f"  Total keys:       {stats['total_keys']}")

    # Test retrieval with a known HN ID
    test_hn_id = 47001871  # Monosketch

    print(f"\n\nTesting retrieval for HN ID: {test_hn_id}")
    print("-" * 70)

    # Check existence
    has_html = await store.html_content_exists(test_hn_id)
    has_text = await store.text_content_exists(test_hn_id)
    has_markdown = await store.markdown_content_exists(test_hn_id)

    print(f"Content exists:")
    print(f"  HTML:     {has_html}")
    print(f"  Text:     {has_text}")
    print(f"  Markdown: {has_markdown}")

    # Retrieve content
    if has_html:
        html = await store.get_html_content(test_hn_id)
        print(f"\nHTML content: {len(html)} characters")
        print(f"Preview: {html[:200]}...")

    if has_text:
        text = await store.get_text_content(test_hn_id)
        print(f"\nText content: {len(text)} characters")
        print(f"Preview: {text[:200]}...")

    if has_markdown:
        markdown = await store.get_markdown_content(test_hn_id)
        print(f"\nMarkdown content: {len(markdown)} characters")
        print(f"Preview:\n{markdown[:400]}...")

    print("\n" + "=" * 70)
    print("✅ RocksDB retrieval test completed successfully!")
    print("=" * 70)

    store.close()


if __name__ == "__main__":
    asyncio.run(main())
