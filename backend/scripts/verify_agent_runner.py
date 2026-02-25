"""Verify openai-agents Runner.run() output structure.

Confirms that the syntax used in summarize_for_users_in_group is correct:
  - Runner.run(agent, input=text)  →  RunResult
  - result.final_output            →  str
  - result.raw_responses           →  list[ModelResponse]
  - raw_response.usage.input_tokens / .output_tokens / .total_tokens

Run:  uv run python scripts/verify_agent_runner.py
Requires OPENAI_API_KEY in env (or .env at project root).
"""

import asyncio
import os
import sys
from pathlib import Path

# Load .env from project root
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv

    load_dotenv(project_root / ".env")
except ImportError:
    pass

if not os.getenv("OPENAI_API_KEY"):
    print("✗ OPENAI_API_KEY not set — set it in .env or environment and retry")
    sys.exit(1)

from agents import Agent, Runner  # noqa: E402


async def main() -> None:
    agent = Agent(
        name="verifier",
        instructions="Reply with exactly three words.",
        model="gpt-4o-mini",
    )

    print("Running Runner.run(agent, input=...) …")
    result = await Runner.run(agent, input="Say hello world")

    print()
    print("=== result type ===")
    print(type(result))

    print()
    print("=== result.final_output ===")
    print(repr(result.final_output))

    print()
    print("=== result.raw_responses ===")
    print(f"  count: {len(result.raw_responses)}")
    for i, r in enumerate(result.raw_responses):
        u = r.usage
        print(f"  [{i}] type(usage) = {type(u)}")
        print(f"  [{i}] usage.input_tokens  = {u.input_tokens}")
        print(f"  [{i}] usage.output_tokens = {u.output_tokens}")
        print(f"  [{i}] usage.total_tokens  = {u.total_tokens}")

    # Replicate exactly the aggregation in summarize_for_users_in_group
    input_tokens = sum(r.usage.input_tokens for r in result.raw_responses)
    output_tokens = sum(r.usage.output_tokens for r in result.raw_responses)
    total = input_tokens + output_tokens

    print()
    print("=== aggregated (as used in summarize_for_users_in_group) ===")
    print(f"  input_tokens  = {input_tokens}")
    print(f"  output_tokens = {output_tokens}")
    print(f"  total         = {total}")

    # Confirm final_output is the text
    summary_text = str(result.final_output).strip()
    print()
    print(f"=== str(result.final_output).strip() = {repr(summary_text)} ===")
    print()
    print("✓ All fields resolved — syntax in summarize_for_users_in_group is correct")


if __name__ == "__main__":
    asyncio.run(main())
