"""Tool for reading previously saved analysis files.

Used by the agent to recall intermediate results for synthesis.
"""

import logging
from pathlib import Path

from agents import function_tool

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/agent_outputs")


def create_file_reader():
    """Create a file_reader tool.

    Returns:
        FunctionTool for reading files from disk.
    """

    @function_tool
    def file_reader(filename: str) -> str:
        """Read a previously saved file from disk.

        Use this to recall intermediate analysis results or batch summaries
        that were saved earlier via file_writer.

        Args:
            filename: Name of the file to read. Can be the full filename
                (including timestamp prefix) or just the base name.

        Returns:
            The file contents, or an error message if not found.
        """
        if not OUTPUT_DIR.exists():
            return "Error: No saved files found. The output directory does not exist."

        safe_name = filename.replace("/", "_").replace("..", "_")

        candidates = list(OUTPUT_DIR.glob(f"*{safe_name}"))
        if not candidates:
            candidates = list(OUTPUT_DIR.glob(safe_name))

        if not candidates:
            available = [f.name for f in sorted(OUTPUT_DIR.iterdir())]
            if available:
                recent = available[-5:]
                return (
                    f"Error: File '{filename}' not found.\n"
                    f"Most recent files: {', '.join(recent)}"
                )
            return f"Error: File '{filename}' not found. No saved files exist yet."

        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        file_path = candidates[0]

        content = file_path.read_text(encoding="utf-8")
        logger.info(f"file_reader: read {len(content)} chars from {file_path}")
        return content

    return file_reader
