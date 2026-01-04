#!/usr/bin/env python
"""Test multi-provider LLM integration."""

import asyncio
import sys
from pathlib import Path

# Fix Windows encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from newsanalysis.core.config import Config
from newsanalysis.database.connection import DatabaseConnection, init_database
from newsanalysis.integrations.provider_factory import ProviderFactory


async def test_all_clients():
    """Test all configured LLM clients."""
    print("\n" + "=" * 70)
    print("MULTI-PROVIDER LLM TEST SUITE")
    print("=" * 70)
    print()

    config = Config()
    db = init_database(Path(config.db_path))

    factory = ProviderFactory(
        config=config,
        db=db,
        run_id="test-multi-provider",
    )

    # Test messages
    test_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'Success' in one word."},
    ]

    results = {
        "classification": None,
        "summarization": None,
        "digest": None,
    }

    # Test 1: Classification Client (DeepSeek by default)
    print("Test 1: Classification Client")
    print("-" * 70)
    try:
        client = factory.get_classification_client()
        print(f"Provider: {config.classification_provider}")

        response = await client.create_completion(
            messages=test_messages,
            module="test",
            request_type="test_classification",
        )

        print(f"  Response: {response['content']}")
        print(f"  Input tokens: {response['usage']['input_tokens']}")
        print(f"  Output tokens: {response['usage']['output_tokens']}")
        print(f"  Cost: ${response['usage']['cost']:.6f}")

        results["classification"] = "PASS"
        print("  Status: PASS")
    except Exception as e:
        print(f"  Status: FAIL - {e}")
        results["classification"] = f"FAIL: {e}"

    print()

    # Test 2: Summarization Client (Gemini by default)
    print("Test 2: Summarization Client")
    print("-" * 70)
    try:
        client = factory.get_summarization_client()
        print(f"Provider: {config.summarization_provider}")

        response = await client.create_completion(
            messages=test_messages,
            module="test",
            request_type="test_summarization",
        )

        print(f"  Response: {response['content']}")
        print(f"  Input tokens: {response['usage']['input_tokens']}")
        print(f"  Output tokens: {response['usage']['output_tokens']}")
        print(f"  Cost: ${response['usage']['cost']:.6f}")

        results["summarization"] = "PASS"
        print("  Status: PASS")
    except Exception as e:
        print(f"  Status: FAIL - {e}")
        results["summarization"] = f"FAIL: {e}"

    print()

    # Test 3: Digest Client (Gemini by default)
    print("Test 3: Digest Client")
    print("-" * 70)
    try:
        client = factory.get_digest_client()
        print(f"Provider: {config.digest_provider}")

        response = await client.create_completion(
            messages=test_messages,
            module="test",
            request_type="test_digest",
        )

        print(f"  Response: {response['content']}")
        print(f"  Input tokens: {response['usage']['input_tokens']}")
        print(f"  Output tokens: {response['usage']['output_tokens']}")
        print(f"  Cost: ${response['usage']['cost']:.6f}")

        results["digest"] = "PASS"
        print("  Status: PASS")
    except Exception as e:
        print(f"  Status: FAIL - {e}")
        results["digest"] = f"FAIL: {e}"

    print()

    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print()

    all_passed = True
    for test_name, result in results.items():
        status = result if result == "PASS" else f"FAIL"
        emoji = "✓" if result == "PASS" else "✗"
        print(f"{emoji} {test_name.capitalize()} Client: {status}")
        if result != "PASS":
            all_passed = False

    print()
    print("=" * 70)

    if all_passed:
        print("ALL TESTS PASSED - Multi-provider migration successful!")
    else:
        print("SOME TESTS FAILED - Please review errors above")

    print("=" * 70)
    print()

    db.close()

    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(test_all_clients())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
