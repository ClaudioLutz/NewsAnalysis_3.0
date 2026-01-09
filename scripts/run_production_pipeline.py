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

        # Article processing statistics
        print("\nArticle Processing:")
        if stats.get("collected", 0) > 0:
            print(f"  Collected:     {stats['collected']:>6} articles")

        if stats.get("filtered", 0) > 0:
            filtered = stats['filtered']
            matched = stats.get("matched", 0)
            rejected = stats.get("rejected", 0)
            match_rate = (matched / filtered * 100) if filtered > 0 else 0
            print(f"  Filtered:      {filtered:>6} articles")
            print(f"    - Matched:   {matched:>6} ({match_rate:.1f}%)")
            print(f"    - Rejected:  {rejected:>6} ({100-match_rate:.1f}%)")

        if stats.get("scraped", 0) > 0:
            print(f"  Scraped:       {stats['scraped']:>6} articles (skipped - Playwright not installed)")

        if stats.get("deduplicated", 0) > 0:
            dedup = stats['deduplicated']
            dupes = stats.get("duplicates_found", 0)
            print(f"  Deduplicated:  {dedup:>6} articles checked ({dupes} duplicates found)")

        if stats.get("summarized", 0) > 0:
            print(f"  Summarized:    {stats['summarized']:>6} articles")

        if stats.get("digested", 0) > 0:
            print(f"  Digested:      {stats['digested']:>6} digest(s) generated")

        # Get run metrics from database
        run_result = db.execute(
            """
            SELECT total_cost, total_tokens, duration_seconds
            FROM pipeline_runs
            WHERE run_id = ?
            """,
            (orchestrator.run_id,)
        )
        run_row = run_result.fetchone()

        if run_row:
            total_cost = run_row['total_cost'] or 0.0
            total_tokens = run_row['total_tokens'] or 0
            duration = run_row['duration_seconds']

            # API costs and tokens
            print("\nAPI Usage & Costs:")
            if total_cost > 0:
                print(f"  Total Cost:    ${total_cost:>8.4f}")
                print(f"  Total Tokens:  {total_tokens:>9,}")

                # Cost breakdown by provider
                provider_result = db.execute(
                    """
                    SELECT
                        CASE
                            WHEN model LIKE 'deepseek%' THEN 'DeepSeek'
                            WHEN model LIKE 'gemini%' THEN 'Gemini'
                            WHEN model LIKE 'gpt%' OR model LIKE 'o1%' THEN 'OpenAI'
                            ELSE 'Other'
                        END as provider,
                        COALESCE(SUM(cost), 0.0) as provider_cost,
                        COALESCE(SUM(total_tokens), 0) as provider_tokens,
                        COUNT(*) as calls
                    FROM api_calls
                    WHERE run_id = ?
                    GROUP BY provider
                    ORDER BY provider_cost DESC
                    """,
                    (orchestrator.run_id,)
                )
                provider_rows = provider_result.fetchall()

                if provider_rows:
                    print("\n  By Provider:")
                    for row in provider_rows:
                        provider = row['provider']
                        cost = row['provider_cost']
                        tokens = row['provider_tokens']
                        calls = row['calls']
                        pct = (cost / total_cost * 100) if total_cost > 0 else 0
                        print(f"    {provider:<10} ${cost:>8.4f} ({pct:>5.1f}%)  |  {tokens:>9,} tokens  |  {calls:>4} calls")

                # Cost breakdown by module
                module_result = db.execute(
                    """
                    SELECT
                        module,
                        COALESCE(SUM(cost), 0.0) as module_cost,
                        COALESCE(SUM(total_tokens), 0) as module_tokens,
                        COUNT(*) as calls
                    FROM api_calls
                    WHERE run_id = ?
                    GROUP BY module
                    ORDER BY module_cost DESC
                    """,
                    (orchestrator.run_id,)
                )
                module_rows = module_result.fetchall()

                if module_rows:
                    print("\n  By Module:")
                    for row in module_rows:
                        module = row['module']
                        cost = row['module_cost']
                        tokens = row['module_tokens']
                        calls = row['calls']
                        pct = (cost / total_cost * 100) if total_cost > 0 else 0
                        print(f"    {module:<15} ${cost:>8.4f} ({pct:>5.1f}%)  |  {tokens:>9,} tokens  |  {calls:>4} calls")

                # Compare with OpenAI estimate
                openai_equivalent = total_cost * 15  # Rough estimate
                savings = openai_equivalent - total_cost
                savings_pct = (savings / openai_equivalent * 100) if openai_equivalent > 0 else 0

                print("\n  Estimated Savings vs OpenAI-only:")
                print(f"    OpenAI estimate: ${openai_equivalent:>8.4f}")
                print(f"    Savings:         ${savings:>8.4f} ({savings_pct:.1f}%)")

            # Duration
            if duration:
                minutes = int(duration // 60)
                seconds = duration % 60
                print(f"\n  Duration:      {minutes}m {seconds:.1f}s")

        # Cache performance
        cache_result = db.execute(
            """
            SELECT
                cache_type,
                requests,
                hits,
                misses,
                hit_rate,
                api_calls_saved,
                cost_saved
            FROM cache_stats
            WHERE date = date('now')
            ORDER BY cache_type
            """
        )
        cache_rows = cache_result.fetchall()

        if cache_rows:
            print("\nCache Performance (Today):")
            for row in cache_rows:
                cache_type = row['cache_type']
                requests = row['requests']
                hits = row['hits']
                hit_rate = row['hit_rate']
                cost_saved = row['cost_saved']
                if requests > 0:
                    print(f"  {cache_type.capitalize():<15} Hit Rate: {hit_rate:>5.1f}%  |  {hits}/{requests} hits  |  ${cost_saved:>7.4f} saved")

        # Show final database state
        cursor = db.execute("""
            SELECT pipeline_stage, COUNT(*) as count
            FROM articles
            GROUP BY pipeline_stage
        """)

        print("\nFinal Database State:")
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
