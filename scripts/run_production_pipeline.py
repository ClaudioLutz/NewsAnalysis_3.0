#!/usr/bin/env python
"""Run production pipeline using orchestrator (bypasses CLI to avoid Playwright import)."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Fix Windows encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from newsanalysis.core.config import Config, PipelineConfig
from newsanalysis.database.connection import init_database


# Monkey-patch playwright_scraper to avoid import error
import newsanalysis.pipeline.scrapers.playwright_scraper as playwright_module
playwright_module.PlaywrightExtractor = None  # Disable Playwright


from newsanalysis.pipeline.orchestrator import PipelineOrchestrator
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Run full production pipeline."""
    print("\n" + "=" * 70)
    print("PRODUCTION PIPELINE - Multi-Provider LLM System")
    print("=" * 70)
    print()

    # Initialize
    config = Config()
    db = init_database(Path(config.db_path))

    print("Provider Configuration:")
    print(f"  Classification: {config.classification_provider}")
    print(f"  Summarization: {config.summarization_provider}")
    print(f"  Digest: {config.digest_provider}")
    print()

    # Configure pipeline
    pipeline_config = PipelineConfig(
        limit=15,  # Process max 15 articles per feed
        skip_scraping=True,  # Skip scraping (Playwright not installed)
        skip_summarization=False,
        skip_digest=False,
        skip_collection=False,
        skip_filtering=False,
    )

    # Create orchestrator
    orchestrator = PipelineOrchestrator(
        config=config,
        db=db,
        pipeline_config=pipeline_config,
    )

    print(f"Run ID: {orchestrator.run_id}")
    print()

    # Show initial state
    cursor = db.execute("""
        SELECT pipeline_stage, COUNT(*) as count
        FROM articles
        GROUP BY pipeline_stage
    """)

    print("Initial Database State:")
    for row in cursor.fetchall():
        print(f"  {row['pipeline_stage']}: {row['count']}")
    print()

    # Run pipeline
    print("=" * 70)
    print("RUNNING PIPELINE")
    print("=" * 70)
    print()

    try:
        stats = await orchestrator.run()

        print()
        print("=" * 70)
        print("PIPELINE RESULTS")
        print("=" * 70)
        print()
        print(f"Collected: {stats['collected']} new articles")
        print(f"Filtered: {stats['filtered']} articles processed")
        print(f"  - Matched: {stats['matched']} relevant")
        print(f"  - Rejected: {stats['rejected']} not relevant")
        print(f"Scraped: {stats['scraped']} (skipped - Playwright not installed)")
        print(f"Summarized: {stats['summarized']} articles")
        print(f"Digest: {stats['digested']} generated")
        print()

        # Show costs by provider
        print("=" * 70)
        print("COST BREAKDOWN BY PROVIDER")
        print("=" * 70)
        print()

        cursor = db.execute("""
            SELECT
                CASE
                    WHEN model LIKE 'deepseek:%' THEN 'DeepSeek'
                    WHEN model LIKE 'gemini:%' THEN 'Gemini'
                    ELSE 'OpenAI'
                END as provider,
                request_type,
                COUNT(*) as calls,
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(cost) as total_cost
            FROM api_calls
            WHERE run_id = ?
            GROUP BY provider, request_type
            ORDER BY provider, request_type
        """, (orchestrator.run_id,))

        current_provider = None
        provider_totals = {}

        for row in cursor.fetchall():
            provider = row['provider']
            request_type = row['request_type']
            calls = row['calls']
            cost = row['total_cost']

            if provider != current_provider:
                if current_provider:
                    print()
                current_provider = provider
                print(f"{provider}:")
                provider_totals[provider] = 0.0

            print(f"  {request_type:<25} {calls:>6} calls  ${cost:>10.6f}")
            provider_totals[provider] += cost

        print()
        print("-" * 70)
        print("Provider Totals:")
        total_cost = 0.0
        for provider, cost in provider_totals.items():
            print(f"  {provider:<30} ${cost:>10.6f}")
            total_cost += cost

        print("-" * 70)
        print(f"  {'TOTAL':<30} ${total_cost:>10.6f}")
        print()

        # Compare with OpenAI
        openai_equivalent = total_cost * 15  # Rough estimate
        savings = openai_equivalent - total_cost
        savings_pct = (savings / openai_equivalent * 100) if openai_equivalent > 0 else 0

        print("Estimated Cost Comparison:")
        print(f"  Multi-Provider (DeepSeek + Gemini): ${total_cost:.6f}")
        print(f"  OpenAI Only (estimated):             ${openai_equivalent:.6f}")
        print(f"  Savings:                             ${savings:.6f} ({savings_pct:.1f}%)")
        print()

        # Show final database state
        cursor = db.execute("""
            SELECT pipeline_stage, COUNT(*) as count
            FROM articles
            GROUP BY pipeline_stage
        """)

        print("Final Database State:")
        for row in cursor.fetchall():
            print(f"  {row['pipeline_stage']}: {row['count']}")
        print()

        print("=" * 70)
        print("✓ PRODUCTION PIPELINE COMPLETE!")
        print("=" * 70)
        print()

    except Exception as e:
        print(f"\nPipeline Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    db.close()
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
