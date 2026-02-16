#!/usr/bin/env python
"""Simple test script for summarization agent - tests configuration and prompt loading."""

import os
import sys
from pathlib import Path

# Load environment variables from .env
from dotenv import load_dotenv

# Load .env file with absolute path
env_path = Path("/Users/nhuantran/Working/learn/hackernews_digest/backend/.env")
load_dotenv(env_path)

# Verify OpenAI API key is loaded
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY not found in .env file")
    sys.exit(1)

print(f"✓ OpenAI API Key loaded (first 20 chars: {api_key[:20]}...)")

# Now test the agent
from app.infrastructure.agents.summarization_agent import (
    create_summarization_agent,
    SummaryOutput,
)


def print_section(title: str):
    """Print a formatted section title."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_agent_creation():
    """Test creating different agent variants."""
    print_section("Test 1: Agent Creation and Configuration")

    variants = ["basic", "technical", "business", "concise", "personalized"]
    results = []

    for variant in variants:
        try:
            agent = create_summarization_agent(prompt_type=variant)

            print(f"✓ Created {variant} agent:")
            print(f"  Name: {agent.name}")
            print(f"  Model: {agent.model}")
            print(f"  Temperature: {agent.temperature}")
            print(f"  Max tokens: {agent.max_tokens}")
            print(f"  Instructions length: {len(agent.instructions)} chars")
            print(f"  First 100 chars: {agent.instructions[:100]}...")
            print()

            results.append((variant, True))
        except Exception as e:
            print(f"✗ Error creating {variant} agent: {e}\n")
            results.append((variant, False))

    passed = sum(1 for _, result in results if result)
    print(f"Summary: {passed}/{len(results)} variants created successfully")
    return all(result for _, result in results)


def test_structured_output():
    """Test SummaryOutput model."""
    print_section("Test 2: SummaryOutput Model")

    try:
        # Test with full data
        summary1 = SummaryOutput(
            summary="PostgreSQL 18 brings major performance improvements.",
            key_points=[
                "2x throughput improvement",
                "New JSON indexing",
                "Async I/O support",
            ],
            technical_level="advanced",
            confidence=0.95,
        )
        print(f"✓ Created SummaryOutput with full data:")
        print(f"  Summary: {summary1.summary}")
        print(f"  Key points: {len(summary1.key_points)}")
        print(f"  Technical level: {summary1.technical_level}")
        print(f"  Confidence: {summary1.confidence}")
        print()

        # Test with defaults
        summary2 = SummaryOutput(summary="Quick summary")
        print(f"✓ Created SummaryOutput with defaults:")
        print(f"  Summary: {summary2.summary}")
        print(f"  Key points: {summary2.key_points}")
        print(f"  Technical level: {summary2.technical_level}")
        print(f"  Confidence: {summary2.confidence}")
        print()

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_prompt_loading():
    """Test loading different prompt variants."""
    print_section("Test 3: Prompt File Loading")

    prompts_dir = Path("/Users/nhuantran/Working/learn/hackernews_digest/backend/app/infrastructure/prompts")
    variants = ["basic", "technical", "business", "concise", "personalized"]

    results = []
    for variant in variants:
        prompt_file = prompts_dir / f"summarizer_{variant}.md"
        try:
            if prompt_file.exists():
                content = prompt_file.read_text(encoding="utf-8")
                print(f"✓ {variant}: {prompt_file.name}")
                print(f"  Size: {len(content)} bytes")
                print(f"  Preview: {content[:80]}...")
                print()
                results.append((variant, True))
            else:
                print(f"✗ {variant}: FILE NOT FOUND")
                print(f"  Expected: {prompt_file}")
                print()
                results.append((variant, False))
        except Exception as e:
            print(f"✗ {variant}: Error reading file: {e}\n")
            results.append((variant, False))

    passed = sum(1 for _, result in results if result)
    print(f"Summary: {passed}/{len(results)} prompts found and readable")
    return all(result for _, result in results)


def test_agent_tools_and_output():
    """Test agent configuration for tools and output."""
    print_section("Test 4: Agent Tools and Output Configuration")

    try:
        # Test basic agent
        agent = create_summarization_agent(prompt_type="basic", use_structured_output=False)
        print(f"✓ Basic agent (no structured output):")
        print(f"  Output type: {agent.agent.output_type}")
        print(f"  Tools: {len(agent.agent.tools)}")
        print()

        # Test with structured output
        agent_structured = create_summarization_agent(
            prompt_type="basic", use_structured_output=True
        )
        print(f"✓ Structured agent:")
        print(f"  Output type: {agent_structured.agent.output_type}")
        print(f"  Output is SummaryOutput: {agent_structured.agent.output_type is SummaryOutput}")
        print()

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_properties():
    """Test agent internal properties."""
    print_section("Test 5: Agent Properties and Methods")

    try:
        agent = create_summarization_agent(prompt_type="technical")

        print(f"✓ Agent properties:")
        print(f"  name: {agent.name}")
        print(f"  model: {agent.model}")
        print(f"  temperature: {agent.temperature}")
        print(f"  max_tokens: {agent.max_tokens}")
        print()

        print(f"✓ Agent SDK wrapper properties:")
        print(f"  agent.agent type: {type(agent.agent).__name__}")
        print(f"  agent.agent.name: {agent.agent.name}")
        print(f"  agent.agent.model: {agent.agent.model}")
        print()

        # List available methods on the agent
        methods = [m for m in dir(agent.agent) if not m.startswith("_")]
        print(f"✓ Available methods on agent.agent: {methods}")
        print()

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_environment():
    """Test environment configuration."""
    print_section("Test 6: Environment Configuration")

    try:
        from app.infrastructure.agents.config import settings

        print(f"✓ Agent settings loaded:")
        print(f"  OpenAI API Key: {'CONFIGURED' if settings.openai_api_key else 'NOT CONFIGURED'}")
        print(f"  OpenAI Model: {settings.openai_model}")
        print(f"  Default Temperature: {settings.openai_default_temperature}")
        print(f"  Default Max Tokens: {settings.openai_default_max_tokens}")
        print(f"  Langfuse Enabled: {settings.langfuse_enabled}")
        print(f"  Track Token Usage: {settings.track_token_usage}")
        print()

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all tests."""
    print_section("Summarization Agent Configuration Tests")

    tests = [
        ("Agent Creation", test_agent_creation),
        ("SummaryOutput Model", test_structured_output),
        ("Prompt Loading", test_prompt_loading),
        ("Tools and Output Configuration", test_agent_tools_and_output),
        ("Agent Properties", test_agent_properties),
        ("Environment Configuration", test_environment),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print_section("Test Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
