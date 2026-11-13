"""Tool for writing analysis results to disk.

Used by the agent to persist intermediate findings, batch summaries,
and synthesized research notes.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from agents import function_tool

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/agent_outputs")


def create_file_writer():
    """Create a file_writer tool.

    Returns:
        FunctionTool for writing content to files on disk.
    """

    @function_tool
    def file_writer(filename: str, content: str) -> str:
        """Write content to a file on disk for later reference.

        Use this to save intermediate analysis results, batch summaries,
        or research notes. Files are saved with a timestamp prefix.

        Args:
            filename: Name of the file (e.g., "rust_analysis_notes.md").
                A timestamp prefix will be added automatically.
            content: The text content to write to the file.

        Returns:
            Confirmation message with the full file path.
        """
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        safe_name = filename.replace("/", "_").replace("..", "_")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        full_name = f"{timestamp}_{safe_name}"
        file_path = OUTPUT_DIR / full_name

        file_path.write_text(content, encoding="utf-8")

        logger.info(f"file_writer: wrote {len(content)} chars to {file_path}")
        return f"File written successfully: {file_path}"

    return file_writer
