"""Unit tests for RocksDB content store."""

import asyncio
import tempfile
import shutil
from pathlib import Path

import pytest

from app.infrastructure.storage.rocksdb_store import RocksDBContentStore


class TestRocksDBContentStore:
    """Test RocksDB content storage."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database directory."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.rocksdb"
        yield str(db_path)
        # Cleanup
        if db_path.exists():
            shutil.rmtree(db_path)

    @pytest.mark.asyncio
    async def test_save_and_retrieve_html(self, temp_db_path):
        """Test saving and retrieving HTML content."""
        store = RocksDBContentStore(db_path=temp_db_path, read_only=False)

        hn_id = 12345
        html_content = "<html><body>Test content</body></html>"

        # Save
        await store.save_html_content(hn_id, html_content)

        # Retrieve
        retrieved = await store.get_html_content(hn_id)

        assert retrieved == html_content
        store.close()

    @pytest.mark.asyncio
    async def test_save_and_retrieve_text(self, temp_db_path):
        """Test saving and retrieving text content."""
        store = RocksDBContentStore(db_path=temp_db_path, read_only=False)

        hn_id = 12345
        text_content = "This is plain text content for testing."

        # Save
        await store.save_text_content(hn_id, text_content)

        # Retrieve
        retrieved = await store.get_text_content(hn_id)

        assert retrieved == text_content
        store.close()

    @pytest.mark.asyncio
    async def test_save_and_retrieve_markdown(self, temp_db_path):
        """Test saving and retrieving markdown content."""
        store = RocksDBContentStore(db_path=temp_db_path, read_only=False)

        hn_id = 12345
        markdown_content = "# Test\n\nThis is **markdown** content."

        # Save
        await store.save_markdown_content(hn_id, markdown_content)

        # Retrieve
        retrieved = await store.get_markdown_content(hn_id)

        assert retrieved == markdown_content
        store.close()

    @pytest.mark.asyncio
    async def test_save_all_formats(self, temp_db_path):
        """Test saving all three content formats."""
        store = RocksDBContentStore(db_path=temp_db_path, read_only=False)

        hn_id = 12345
        html = "<html><body>HTML</body></html>"
        text = "Plain text"
        markdown = "# Markdown"

        # Save all
        await store.save_all(hn_id, html, text, markdown)

        # Retrieve all
        retrieved_html = await store.get_html_content(hn_id)
        retrieved_text = await store.get_text_content(hn_id)
        retrieved_markdown = await store.get_markdown_content(hn_id)

        assert retrieved_html == html
        assert retrieved_text == text
        assert retrieved_markdown == markdown
        store.close()

    @pytest.mark.asyncio
    async def test_content_exists(self, temp_db_path):
        """Test checking if content exists."""
        store = RocksDBContentStore(db_path=temp_db_path, read_only=False)

        hn_id = 12345

        # Check before save
        assert await store.html_content_exists(hn_id) is False
        assert await store.text_content_exists(hn_id) is False
        assert await store.markdown_content_exists(hn_id) is False

        # Save content
        await store.save_html_content(hn_id, "<html>Test</html>")
        await store.save_text_content(hn_id, "Test text")
        await store.save_markdown_content(hn_id, "# Test")

        # Check after save
        assert await store.html_content_exists(hn_id) is True
        assert await store.text_content_exists(hn_id) is True
        assert await store.markdown_content_exists(hn_id) is True

        store.close()

    @pytest.mark.asyncio
    async def test_get_nonexistent_content(self, temp_db_path):
        """Test retrieving non-existent content returns None."""
        store = RocksDBContentStore(db_path=temp_db_path, read_only=False)

        hn_id = 99999

        retrieved_html = await store.get_html_content(hn_id)
        retrieved_text = await store.get_text_content(hn_id)
        retrieved_markdown = await store.get_markdown_content(hn_id)

        assert retrieved_html is None
        assert retrieved_text is None
        assert retrieved_markdown is None

        store.close()

    @pytest.mark.asyncio
    async def test_delete_content(self, temp_db_path):
        """Test deleting all content for a post."""
        store = RocksDBContentStore(db_path=temp_db_path, read_only=False)

        hn_id = 12345

        # Save content
        await store.save_all(
            hn_id,
            "<html>Test</html>",
            "Test text",
            "# Test"
        )

        # Verify exists
        assert await store.html_content_exists(hn_id) is True

        # Delete
        store.delete(hn_id)

        # Verify deleted
        assert await store.html_content_exists(hn_id) is False
        assert await store.text_content_exists(hn_id) is False
        assert await store.markdown_content_exists(hn_id) is False

        store.close()

    @pytest.mark.asyncio
    async def test_get_stats(self, temp_db_path):
        """Test getting database statistics."""
        store = RocksDBContentStore(db_path=temp_db_path, read_only=False)

        # Save multiple posts
        for hn_id in [100, 200, 300]:
            await store.save_all(
                hn_id,
                f"<html>Post {hn_id}</html>",
                f"Text {hn_id}",
                f"# Post {hn_id}"
            )

        stats = store.get_stats()

        assert stats["html_count"] == 3
        assert stats["text_count"] == 3
        assert stats["markdown_count"] == 3
        assert stats["total_keys"] == 9
        assert temp_db_path in stats["db_path"]

        store.close()

    @pytest.mark.asyncio
    async def test_multiple_posts(self, temp_db_path):
        """Test storing content for multiple posts."""
        store = RocksDBContentStore(db_path=temp_db_path, read_only=False)

        posts = {
            100: ("HTML 1", "Text 1", "MD 1"),
            200: ("HTML 2", "Text 2", "MD 2"),
            300: ("HTML 3", "Text 3", "MD 3"),
        }

        # Save all posts
        for hn_id, (html, text, md) in posts.items():
            await store.save_all(hn_id, html, text, md)

        # Verify all posts
        for hn_id, (html, text, md) in posts.items():
            assert await store.get_html_content(hn_id) == html
            assert await store.get_text_content(hn_id) == text
            assert await store.get_markdown_content(hn_id) == md

        store.close()

    @pytest.mark.asyncio
    async def test_unicode_content(self, temp_db_path):
        """Test storing Unicode content."""
        store = RocksDBContentStore(db_path=temp_db_path, read_only=False)

        hn_id = 12345
        unicode_content = "Hello 世界! 🚀 Testing émojis and spëcial çharacters"

        await store.save_text_content(hn_id, unicode_content)
        retrieved = await store.get_text_content(hn_id)

        assert retrieved == unicode_content
        store.close()

    @pytest.mark.asyncio
    async def test_large_content(self, temp_db_path):
        """Test storing large content."""
        store = RocksDBContentStore(db_path=temp_db_path, read_only=False)

        hn_id = 12345
        large_content = "A" * 1_000_000  # 1MB of data

        await store.save_html_content(hn_id, large_content)
        retrieved = await store.get_html_content(hn_id)

        assert len(retrieved) == 1_000_000
        assert retrieved == large_content
        store.close()

    @pytest.mark.asyncio
    async def test_context_manager(self, temp_db_path):
        """Test using store as context manager."""
        hn_id = 12345
        test_content = "Test content"

        with RocksDBContentStore(db_path=temp_db_path, read_only=False) as store:
            await store.save_text_content(hn_id, test_content)
            retrieved = await store.get_text_content(hn_id)
            assert retrieved == test_content

        # Verify store was closed (new instance should be able to open)
        with RocksDBContentStore(db_path=temp_db_path, read_only=False) as store2:
            retrieved2 = await store2.get_text_content(hn_id)
            assert retrieved2 == test_content
