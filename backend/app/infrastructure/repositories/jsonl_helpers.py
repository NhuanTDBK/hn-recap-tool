"""JSONL file helpers for reading and writing data.

Provides utilities for working with JSONL (newline-delimited JSON) files
with optional gzip compression.
"""

import json
import gzip
from pathlib import Path
from typing import Generator, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def ensure_directory(file_path: str) -> None:
    """Ensure the directory for a file path exists.

    Args:
        file_path: Path to file
    """
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)


def read_jsonl(file_path: str, compressed: bool = False) -> Generator[dict, None, None]:
    """Read records from a JSONL file.

    Args:
        file_path: Path to JSONL file
        compressed: Whether the file is gzip compressed

    Yields:
        Parsed JSON objects
    """
    if not Path(file_path).exists():
        logger.warning(f"File not found: {file_path}")
        return

    try:
        open_fn = gzip.open if compressed else open
        mode = 'rt' if compressed else 'r'

        with open_fn(file_path, mode, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in {file_path}: {e}")
                        continue
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        raise


def write_jsonl(file_path: str, data: Any, compressed: bool = False, append: bool = True) -> None:
    """Write a single record to a JSONL file.

    Args:
        file_path: Path to JSONL file
        data: Data to write (will be JSON serialized)
        compressed: Whether to gzip compress
        append: Whether to append or overwrite
    """
    ensure_directory(file_path)

    try:
        mode = 'at' if append and not compressed else 'wt'
        if compressed:
            mode = 'at' if append else 'wt'

        open_fn = gzip.open if compressed else open

        with open_fn(file_path, mode, encoding='utf-8') as f:
            json_str = json.dumps(data, default=str)
            f.write(json_str + '\n')
    except Exception as e:
        logger.error(f"Error writing to {file_path}: {e}")
        raise


def write_jsonl_batch(
    file_path: str,
    data_list: List[Any],
    compressed: bool = False,
    append: bool = True
) -> None:
    """Write multiple records to a JSONL file.

    Args:
        file_path: Path to JSONL file
        data_list: List of data to write
        compressed: Whether to gzip compress
        append: Whether to append or overwrite
    """
    ensure_directory(file_path)

    try:
        mode = 'at' if append and not compressed else 'wt'
        if compressed:
            mode = 'at' if append else 'wt'

        open_fn = gzip.open if compressed else open

        with open_fn(file_path, mode, encoding='utf-8') as f:
            for data in data_list:
                json_str = json.dumps(data, default=str)
                f.write(json_str + '\n')
    except Exception as e:
        logger.error(f"Error writing batch to {file_path}: {e}")
        raise


def find_by_field(
    file_path: str,
    field: str,
    value: Any,
    compressed: bool = False
) -> Optional[dict]:
    """Find first record matching a field value.

    Args:
        file_path: Path to JSONL file
        field: Field name to match
        value: Value to match
        compressed: Whether file is compressed

    Returns:
        First matching record or None
    """
    for record in read_jsonl(file_path, compressed=compressed):
        if record.get(field) == value:
            return record
    return None


def filter_by_field(
    file_path: str,
    field: str,
    value: Any,
    compressed: bool = False
) -> List[dict]:
    """Find all records matching a field value.

    Args:
        file_path: Path to JSONL file
        field: Field name to match
        value: Value to match
        compressed: Whether file is compressed

    Returns:
        List of matching records
    """
    results = []
    for record in read_jsonl(file_path, compressed=compressed):
        if record.get(field) == value:
            results.append(record)
    return results


def update_record(
    file_path: str,
    field: str,
    value: Any,
    updated_data: dict,
    compressed: bool = False
) -> bool:
    """Update a record in a JSONL file.

    Note: This reads all records into memory, updates, and rewrites the file.
    Not suitable for very large files.

    Args:
        file_path: Path to JSONL file
        field: Field name to match
        value: Value to match
        updated_data: Updated record data
        compressed: Whether file is compressed

    Returns:
        True if record was found and updated
    """
    if not Path(file_path).exists():
        return False

    records = list(read_jsonl(file_path, compressed=compressed))
    updated = False

    for i, record in enumerate(records):
        if record.get(field) == value:
            records[i] = updated_data
            updated = True
            break

    if updated:
        # Rewrite entire file
        write_jsonl_batch(file_path, records, compressed=compressed, append=False)

    return updated


def count_records(file_path: str, compressed: bool = False) -> int:
    """Count total records in a JSONL file.

    Args:
        file_path: Path to JSONL file
        compressed: Whether file is compressed

    Returns:
        Number of records
    """
    if not Path(file_path).exists():
        return 0

    count = 0
    for _ in read_jsonl(file_path, compressed=compressed):
        count += 1
    return count
