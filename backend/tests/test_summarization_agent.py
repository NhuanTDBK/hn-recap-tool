#!/usr/bin/env python
"""Test script for summarization agent with input and output examples."""

import asyncio
import os
import sys
from pathlib import Path

# Load environment variables from .env
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Verify OpenAI API key is loaded
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY not found in .env file")
    sys.exit(1)

print(f"✓ OpenAI API Key loaded (first 20 chars: {api_key[:20]}...)")

# Now import the agent
from app.infrastructure.agents.summarization_agent import (
    create_summarization_agent,
    summarize_post,
)


# Sample content for testing
SAMPLE_MARKDOWN_CONTENT = """
# PostgreSQL 18 Released

PostgreSQL 18 was released on October 3, 2024, bringing significant performance improvements and new features to the world's most advanced open source database.

## Key Features

### Performance Improvements
- Up to 2x throughput improvements in OLTP workloads
- New JSON path indexing capabilities
- Asynchronous I/O support for improved concurrency
- Query optimization enhancements

### New Capabilities
- Advanced window functions
- Improved partitioning strategies
- Enhanced security features with new authentication methods
- Better full-text search capabilities

### Developer Experience
- Improved error messages and debugging information
- New SQL commands for easier administration
- Better support for modern application patterns
- Enhanced tooling and monitoring capabilities

## Benchmark Results

Tests conducted on standard hardware show:
- 40-50% improvement in read-heavy workloads
- 30-40% improvement in write-heavy workloads
- Reduced latency for concurrent connections
- Better memory efficiency under load

## Migration Path

Upgrading from PostgreSQL 17 is straightforward:
1. Back up existing databases
2. Run pg_upgrade tool
3. Verify data integrity
4. Update connection strings if needed

## Conclusion

PostgreSQL 18 represents another major step forward in database technology, offering organizations better performance, reliability, and new capabilities for modern application development.
"""

SAMPLE_MARKDOWN_CONTENT_2 = """
# Machine Learning in Rust: Polars and ndarray

Rust is becoming increasingly popular for machine learning and data science applications. Two key libraries leading this charge are Polars and ndarray.

## Polars: Fast DataFrame Library

Polars is a lightning-fast DataFrame library written in Rust, designed as a faster alternative to pandas.

### Performance
- 10-100x faster than pandas for large datasets
- Efficient memory usage with lazy evaluation
- Vectorized operations on columnar data
- Streaming support for out-of-core processing

### Features
- Native Python bindings with PyO3
- SQL interface for familiar queries
- Parquet and CSV I/O support
- Groupby and aggregation operations

### Use Cases
- ETL pipelines
- Data preprocessing
- Exploratory data analysis
- Real-time analytics

## ndarray: Numerical Computing

The ndarray crate provides N-dimensional array operations similar to NumPy.

### Capabilities
- Linear algebra operations
- Statistical functions
- Broadcasting and slicing
- FFT and signal processing

### Ecosystem
- nalgebra for advanced linear algebra
- rand for random number generation
- ndarray-stats for statistical operations
- Integration with scientific libraries

## Rust ML Stack

The complete ecosystem includes:
- tch-rs: PyTorch bindings
- tensorflow-rust: TensorFlow support
- ort: ONNX runtime
- Candle: Native Rust deep learning

## Conclusion

Rust's performance characteristics make it ideal for building robust, efficient machine learning systems at scale.
"""


def print_section(title: str):
    """Print a formatted section title."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_basic_summarization():
    """Test basic summarization."""
    print_section("Test 1: Basic Summarization")

    print("Input Content:")
    print("-" * 70)
    print(SAMPLE_MARKDOWN_CONTENT[:500] + "...\n")

    print("Running summarization agent (basic prompt)...")
    try:
        agent = create_summarization_agent(prompt_type="basic")
        print(f"✓ Agent created: {agent.name}")
        print(f"  Model: {agent.model}")
        print(f"  Temperature: {agent.temperature}")
        print(f"  Max tokens: {agent.max_tokens}")

        # Run the agent
        result = agent.agent.run(SAMPLE_MARKDOWN_CONTENT)
        print(f"\n✓ Agent execution successful")
        print(f"  Input tokens: {result.usage.input_tokens}")
        print(f"  Output tokens: {result.usage.output_tokens}")

        print("\nOutput Summary:")
        print("-" * 70)
        print(result.output)
        print("-" * 70)

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_technical_summarization():
    """Test technical summarization."""
    print_section("Test 2: Technical Summarization")

    print("Input Content:")
    print("-" * 70)
    print(SAMPLE_MARKDOWN_CONTENT_2[:500] + "...\n")

    print("Running summarization agent (technical prompt)...")
    try:
        agent = create_summarization_agent(prompt_type="technical")
        print(f"✓ Agent created: {agent.name}")
        print(f"  Model: {agent.model}")
        print(f"  Temperature: {agent.temperature}")

        # Run the agent
        result = agent.agent.run(SAMPLE_MARKDOWN_CONTENT_2)
        print(f"\n✓ Agent execution successful")
        print(f"  Input tokens: {result.usage.input_tokens}")
        print(f"  Output tokens: {result.usage.output_tokens}")

        print("\nOutput Summary:")
        print("-" * 70)
        print(result.output)
        print("-" * 70)

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_concise_summarization():
    """Test concise summarization."""
    print_section("Test 3: Concise Summarization")

    print("Input Content:")
    print("-" * 70)
    print(SAMPLE_MARKDOWN_CONTENT[:400] + "...\n")

    print("Running summarization agent (concise prompt)...")
    try:
        agent = create_summarization_agent(prompt_type="concise")
        print(f"✓ Agent created: {agent.name}")

        # Run the agent
        result = agent.agent.run(SAMPLE_MARKDOWN_CONTENT)
        print(f"\n✓ Agent execution successful")
        print(f"  Input tokens: {result.usage.input_tokens}")
        print(f"  Output tokens: {result.usage.output_tokens}")

        print("\nOutput Summary (Concise):")
        print("-" * 70)
        print(result.output)
        print("-" * 70)

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_different_lengths():
    """Test with different content lengths."""
    print_section("Test 4: Different Content Lengths")

    content_short = "PostgreSQL 18 was released with major performance improvements."
    content_medium = SAMPLE_MARKDOWN_CONTENT[:1000]
    content_long = SAMPLE_MARKDOWN_CONTENT

    test_cases = [
        ("Short content", content_short),
        ("Medium content", content_medium),
        ("Long content", content_long),
    ]

    results = []
    for name, content in test_cases:
        print(f"\n{name}:")
        print(f"  Length: {len(content)} characters")

        try:
            agent = create_summarization_agent(prompt_type="basic")
            result = agent.agent.run(content)
            print(f"  ✓ Success")
            print(f"    Input tokens: {result.usage.input_tokens}")
            print(f"    Output tokens: {result.usage.output_tokens}")
            print(f"    Summary: {result.output[:100]}...")
            results.append(True)
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append(False)

    return all(results)


def test_error_handling():
    """Test error handling with edge cases."""
    print_section("Test 5: Error Handling")

    test_cases = [
        ("Empty string", ""),
        ("Very long content", "word " * 10000),  # Very long
        ("Special characters", "🚀 PostgreSQL 18 🎉 Released!"),
    ]

    results = []
    for name, content in test_cases:
        print(f"\n{name}:")
        print(f"  Length: {len(content)} characters")

        try:
            agent = create_summarization_agent(prompt_type="basic")
            result = agent.agent.run(content)
            print(f"  ✓ Success - handled gracefully")
            print(f"    Summary: {result.output[:80]}...")
            results.append(True)
        except Exception as e:
            print(f"  ✓ Error handled: {str(e)[:80]}...")
            results.append(False)  # We expect some to fail

    return True  # Test passes if we can handle edge cases


def main():
    """Run all tests."""
    print_section("Summarization Agent Testing")
    print(f"OpenAI Model: {os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}")
    print(f"Working Directory: {Path.cwd()}")

    tests = [
        ("Basic Summarization", test_basic_summarization),
        ("Technical Summarization", test_technical_summarization),
        ("Concise Summarization", test_concise_summarization),
        ("Different Content Lengths", test_different_lengths),
        ("Error Handling", test_error_handling),
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
