"""Storage infrastructure for content persistence."""

from .rocksdb_store import RocksDBContentStore

__all__ = ["RocksDBContentStore"]
