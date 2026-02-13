#!/usr/bin/env python3
"""
Migrate existing content files to RocksDB.

This script:
1. Scans existing file-based content (html/, text/, markdown/)
2. Migrates all content to RocksDB
3. Verifies migration completeness

Usage:
    python scripts/migrate_files_to_rocksdb.py
    python scripts/migrate_files_to_rocksdb.py --dry-run
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infrastructure.storage.rocksdb_store import RocksDBContentStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def migrate_files_to_rocksdb(
    source_dir: str = "data/content",
    rocksdb_path: str = "data/content.rocksdb",
    dry_run: bool = False
):
    """Migrate file-based content to RocksDB.

    Args:
        source_dir: Directory containing html/, text/, markdown/ folders
        rocksdb_path: Path to RocksDB database
        dry_run: If True, only report what would be migrated
    """
    source_path = Path(source_dir)
    html_dir = source_path / "html"
    text_dir = source_path / "text"
    markdown_dir = source_path / "markdown"

    # Check if source directories exist
    if not any([html_dir.exists(), text_dir.exists(), markdown_dir.exists()]):
        logger.info("No source directories found. Nothing to migrate.")
        return

    # Initialize RocksDB store
    if not dry_run:
        store = RocksDBContentStore(db_path=rocksdb_path)

    # Collect all HN IDs from files
    hn_ids = set()

    if html_dir.exists():
        for file in html_dir.glob("*.html"):
            hn_id = file.stem
            if hn_id.isdigit():
                hn_ids.add(int(hn_id))

    if text_dir.exists():
        for file in text_dir.glob("*.txt"):
            hn_id = file.stem
            if hn_id.isdigit():
                hn_ids.add(int(hn_id))

    if markdown_dir.exists():
        for file in markdown_dir.glob("*.md"):
            hn_id = file.stem
            if hn_id.isdigit():
                hn_ids.add(int(hn_id))

    logger.info(f"Found {len(hn_ids)} unique HN IDs to migrate")

    # Migrate each HN ID
    migrated = 0
    skipped = 0
    errors = 0

    for hn_id in sorted(hn_ids):
        logger.info(f"Migrating {hn_id}...")

        html_file = html_dir / f"{hn_id}.html"
        text_file = text_dir / f"{hn_id}.txt"
        markdown_file = markdown_dir / f"{hn_id}.md"

        html_content = None
        text_content = None
        markdown_content = None

        # Read HTML
        if html_file.exists():
            try:
                html_content = html_file.read_text(encoding="utf-8")
                logger.debug(f"  Read HTML: {len(html_content)} chars")
            except Exception as e:
                logger.error(f"  Failed to read HTML: {e}")
                errors += 1
                continue

        # Read text
        if text_file.exists():
            try:
                text_content = text_file.read_text(encoding="utf-8")
                logger.debug(f"  Read text: {len(text_content)} chars")
            except Exception as e:
                logger.error(f"  Failed to read text: {e}")
                errors += 1
                continue

        # Read markdown
        if markdown_file.exists():
            try:
                markdown_content = markdown_file.read_text(encoding="utf-8")
                logger.debug(f"  Read markdown: {len(markdown_content)} chars")
            except Exception as e:
                logger.error(f"  Failed to read markdown: {e}")
                errors += 1
                continue

        # Skip if no content
        if not any([html_content, text_content, markdown_content]):
            logger.warning(f"  No content found for {hn_id}, skipping")
            skipped += 1
            continue

        # Save to RocksDB (if not dry run)
        if not dry_run:
            try:
                if html_content:
                    await store.save_html_content(hn_id, html_content)
                if text_content:
                    await store.save_text_content(hn_id, text_content)
                if markdown_content:
                    await store.save_markdown_content(hn_id, markdown_content)

                logger.info(f"  ✓ Migrated {hn_id}")
                migrated += 1
            except Exception as e:
                logger.error(f"  ✗ Failed to migrate {hn_id}: {e}")
                errors += 1
        else:
            logger.info(f"  [DRY RUN] Would migrate {hn_id}")
            migrated += 1

    # Report statistics
    print("\n" + "=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)
    print(f"Total HN IDs:  {len(hn_ids)}")
    print(f"Migrated:      {migrated} ✓")
    print(f"Skipped:       {skipped}")
    print(f"Errors:        {errors} ✗")

    if not dry_run:
        # Show RocksDB stats
        stats = store.get_stats()
        print(f"\nRocksDB Statistics:")
        print(f"  HTML entries:     {stats['html_count']}")
        print(f"  Text entries:     {stats['text_count']}")
        print(f"  Markdown entries: {stats['markdown_count']}")
        print(f"  Total keys:       {stats['total_keys']}")
        print(f"  Database path:    {stats['db_path']}")

        # Close store
        store.close()

    print("=" * 70)

    if dry_run:
        print("\n💡 This was a dry run. Use without --dry-run to perform migration.")
    else:
        print("\n✅ Migration completed!")
        print("\n⚠️  Important: Backup your file-based content before deleting!")
        print(f"   Old files: {source_dir}/{{html,text,markdown}}/")
        print(f"   New database: {rocksdb_path}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate file-based content to RocksDB"
    )
    parser.add_argument(
        "--source-dir",
        type=str,
        default="data/content",
        help="Directory containing html/, text/, markdown/ folders"
    )
    parser.add_argument(
        "--rocksdb-path",
        type=str,
        default="data/content.rocksdb",
        help="Path to RocksDB database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually migrating"
    )

    args = parser.parse_args()

    await migrate_files_to_rocksdb(
        source_dir=args.source_dir,
        rocksdb_path=args.rocksdb_path,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    asyncio.run(main())
