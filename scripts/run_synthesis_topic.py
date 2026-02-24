#!/usr/bin/env python3
"""Script to run topic-focused synthesis on multiple articles.

Usage:
    python scripts/run_synthesis_topic.py "your topic here"
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Add project root and backend to path
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
from agents import Agent, Runner, ModelSettings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_summaries(summaries_file: Path) -> List[Dict]:
    """Load summaries from a JSONL file."""
    summaries = []
    with open(summaries_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                summary = json.loads(line.strip())
                summaries.append(summary)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON line: {e}")
                continue
    return summaries


def save_synthesis(synthesis: str, output_dir: Path, topic: str):
    """Save synthesis to file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    safe_topic = topic.replace(" ", "-").replace("/", "-")
    output_file = output_dir / f"{timestamp}-synthesis-{safe_topic}.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Topic Synthesis: {topic}\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write("---\n\n")
        f.write(synthesis)
        f.write("\n")

    logger.info(f"Saved synthesis to {output_file}")
    return output_file


async def synthesize_by_topic(summaries: List[Dict], topic: str, api_key: str) -> str:
    """Synthesize multiple summaries with a topic focus."""
    # Load topic synthesis prompt
    prompts_dir = backend_dir / "app" / "infrastructure" / "services" / "prompts"
    synthesis_prompt = (prompts_dir / "synthesis_topic.md").read_text()

    # Configure model
    model_settings = ModelSettings(
        max_tokens=800,
        temperature=0.5,
    )

    # Create synthesis agent
    synthesis_agent = Agent(
        name="Topic-Focused Synthesizer",
        instructions=synthesis_prompt,
        model="gpt-4o-mini",
        model_settings=model_settings,
    )

    # Format summaries
    formatted = []
    for i, item in enumerate(summaries, 1):
        title = item.get("title", "Untitled")
        summary = item.get("summary", "")

        formatted.append(f"=== Article {i}: {title} ===")
        formatted.append(f"\nSummary:\n{summary}\n")
        formatted.append("-" * 80)

    formatted_content = "\n".join(formatted)

    # Create prompt
    prompt = (
        f"Topic: {topic}\n\n"
        f"Synthesize insights about '{topic}' from these {len(summaries)} article summaries:\n\n"
        f"{formatted_content}"
    )

    # Run synthesis
    logger.info(f"Running topic-focused synthesis on: {topic}...")
    result = await Runner.run(synthesis_agent, input=prompt)
    synthesis = result.final_output if result.final_output else "[No synthesis generated]"

    return synthesis


async def main():
    """Main function."""
    # Check for topic argument
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_synthesis_topic.py \"your topic here\"")
        print("\nExamples:")
        print("  python scripts/run_synthesis_topic.py \"open source\"")
        print("  python scripts/run_synthesis_topic.py \"artificial intelligence\"")
        print("  python scripts/run_synthesis_topic.py \"education technology\"")
        sys.exit(1)

    topic = " ".join(sys.argv[1:])

    # Load environment
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment")
        sys.exit(1)

    # Setup paths
    data_dir = project_root / "data"
    summaries_dir = data_dir / "processed" / "summaries"
    output_dir = data_dir / "processed" / "synthesis"

    # Find latest summaries file
    summaries_files = sorted(summaries_dir.glob("*.jsonl"))
    if not summaries_files:
        logger.error(f"No summaries files found in {summaries_dir}")
        logger.error("Please run run_summarization.py first")
        sys.exit(1)

    latest_summaries_file = summaries_files[-1]
    logger.info(f"Using summaries file: {latest_summaries_file.name}")

    # Load summaries
    summaries = load_summaries(latest_summaries_file)
    logger.info(f"Loaded {len(summaries)} summaries")

    # Generate topic-focused synthesis
    logger.info("\n" + "=" * 60)
    logger.info(f"GENERATING TOPIC-FOCUSED SYNTHESIS: {topic}")
    logger.info("=" * 60)

    synthesis = await synthesize_by_topic(summaries, topic, api_key)
    output_file = save_synthesis(synthesis, output_dir, topic)

    # Print results
    logger.info("\n" + "=" * 60)
    logger.info("SYNTHESIS COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Topic: {topic}")
    logger.info(f"Output: {output_file}")
    logger.info("=" * 60)

    print("\n" + "=" * 60)
    print("SYNTHESIS CONTENT")
    print("=" * 60)
    print("\n" + synthesis + "\n")


if __name__ == "__main__":
    asyncio.run(main())
