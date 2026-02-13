#!/usr/bin/env python
"""Quick syntax check for agent infrastructure."""

import sys
import traceback

def test_imports():
    """Test that all imports work."""
    try:
        print("Testing imports...")
        from backend.app.infrastructure.agents.config import AgentSettings, settings
        print("  ✓ config.py imports OK")

        from backend.app.infrastructure.agents.token_tracker import TokenTracker, PRICING
        print("  ✓ token_tracker.py imports OK")

        from backend.app.infrastructure.agents.base_agent import BaseAgent, TrackedAgent
        print("  ✓ base_agent.py imports OK")

        from backend.app.infrastructure.agents.summarization_agent import (
            SummaryOutput,
            create_summarization_agent,
            summarize_post,
        )
        print("  ✓ summarization_agent.py imports OK")

        return True
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        traceback.print_exc()
        return False

def test_config():
    """Test configuration."""
    try:
        print("\nTesting configuration...")
        from backend.app.infrastructure.agents.config import settings

        assert settings.openai_model == "gpt-4o-mini", "Default model should be gpt-4o-mini"
        print(f"  ✓ Model: {settings.openai_model}")

        assert settings.openai_default_temperature == 0.7
        print(f"  ✓ Temperature: {settings.openai_default_temperature}")

        assert settings.openai_default_max_tokens == 500
        print(f"  ✓ Max tokens: {settings.openai_default_max_tokens}")

        return True
    except Exception as e:
        print(f"  ✗ Config test failed: {e}")
        traceback.print_exc()
        return False

def test_pricing():
    """Test pricing dictionary."""
    try:
        print("\nTesting pricing...")
        from backend.app.infrastructure.agents.token_tracker import PRICING

        assert "gpt-4o-mini" in PRICING
        assert PRICING["gpt-4o-mini"]["input"] == 0.150
        assert PRICING["gpt-4o-mini"]["output"] == 0.600
        print(f"  ✓ GPT-4o-mini pricing: ${PRICING['gpt-4o-mini']['input']:.3f} input, ${PRICING['gpt-4o-mini']['output']:.3f} output")

        assert "gpt-4o" in PRICING
        print(f"  ✓ GPT-4o pricing: ${PRICING['gpt-4o']['input']:.2f} input, ${PRICING['gpt-4o']['output']:.2f} output")

        return True
    except Exception as e:
        print(f"  ✗ Pricing test failed: {e}")
        traceback.print_exc()
        return False

def test_models():
    """Test model definitions."""
    try:
        print("\nTesting models...")
        from backend.app.infrastructure.database.models import User, UserTokenUsage, AgentCall

        print(f"  ✓ User model: {User.__tablename__}")
        print(f"  ✓ UserTokenUsage model: {UserTokenUsage.__tablename__}")
        print(f"  ✓ AgentCall model: {AgentCall.__tablename__}")

        return True
    except Exception as e:
        print(f"  ✗ Model test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all syntax tests."""
    print("=" * 60)
    print("AGENT INFRASTRUCTURE SYNTAX CHECK")
    print("=" * 60)

    results = [
        ("Imports", test_imports()),
        ("Configuration", test_config()),
        ("Pricing", test_pricing()),
        ("Models", test_models()),
    ]

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:20} {status}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n✓ All syntax checks passed!")
        return 0
    else:
        print("\n✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
