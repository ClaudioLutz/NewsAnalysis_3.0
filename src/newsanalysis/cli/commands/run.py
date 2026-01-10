"""Run pipeline command."""

import asyncio
from typing import Optional

import click

from newsanalysis.core.config import Config, PipelineConfig
from newsanalysis.database.connection import DatabaseConnection
from newsanalysis.pipeline.orchestrator import PipelineOrchestrator
from newsanalysis.utils.logging import setup_logging


@click.command()
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit number of articles to process (for testing)",
)
@click.option(
    "--mode",
    type=click.Choice(["full", "express", "export"]),
    default="full",
    help="Pipeline execution mode",
)
@click.option(
    "--skip-collection",
    is_flag=True,
    help="Skip news collection stage",
)
@click.option(
    "--skip-filtering",
    is_flag=True,
    help="Skip AI filtering stage",
)
@click.option(
    "--skip-scraping",
    is_flag=True,
    help="Skip content scraping stage",
)
@click.option(
    "--skip-summarization",
    is_flag=True,
    help="Skip article summarization stage",
)
@click.option(
    "--skip-digest",
    is_flag=True,
    help="Skip digest generation stage",
)
@click.option(
    "--reset",
    type=click.Choice(["summarization", "digest", "all"]),
    default=None,
    help="Reset articles to reprocess: summarization (re-summarize), digest (re-digest), all (full reprocess)",
)
def run(
    limit: Optional[int],
    mode: str,
    skip_collection: bool,
    skip_filtering: bool,
    skip_scraping: bool,
    skip_summarization: bool,
    skip_digest: bool,
    reset: Optional[str],
) -> None:
    """Run the news analysis pipeline.

    Examples:
        newsanalysis run                        # Run full pipeline
        newsanalysis run --limit 10             # Process only 10 articles
        newsanalysis run --mode express         # Quick mode
        newsanalysis run --skip-digest          # Skip digest generation
        newsanalysis run --reset digest         # Re-generate digest
        newsanalysis run --reset summarization  # Re-summarize all articles
        newsanalysis run --reset all            # Full reprocess from scratch
    """
    # Load configuration
    try:
        config = Config()  # type: ignore
        config.validate_paths()
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        click.echo("Please ensure .env file exists with required settings.", err=True)
        raise click.Abort()

    # Setup logging
    setup_logging(log_level=config.log_level, log_format=config.log_format, log_dir=config.log_dir)

    # Display configuration
    click.echo("NewsAnalysis Pipeline")
    click.echo("=" * 50)
    click.echo(f"Mode: {mode}")
    click.echo(f"Limit: {limit or 'No limit'}")
    click.echo(f"Database: {config.db_path}")
    click.echo(f"Output: {config.output_dir}")
    click.echo("=" * 50)

    # Create pipeline configuration
    pipeline_config = PipelineConfig(
        mode=mode,  # type: ignore
        limit=limit,
        skip_collection=skip_collection,
        skip_filtering=skip_filtering,
        skip_scraping=skip_scraping,
        skip_summarization=skip_summarization,
        skip_digest=skip_digest,
    )

    # Determine which stages will run
    stages = []
    if not skip_collection:
        stages.append("1. News Collection")
    if not skip_filtering:
        stages.append("2. AI Filtering")
    if not skip_scraping:
        stages.append("3. Content Scraping")
    if not skip_summarization:
        stages.append("4. Article Summarization")
    if not skip_digest:
        stages.append("5. Digest Generation")

    if stages:
        click.echo("\nPipeline stages:")
        for stage in stages:
            click.echo(f"  {stage}")
        click.echo()

    # Initialize database connection
    db = DatabaseConnection(config.db_path)

    # Handle reset flag
    if reset:
        _reset_articles(db, reset)

    try:
        # Create and run pipeline orchestrator
        orchestrator = PipelineOrchestrator(
            config=config,
            db=db,
            pipeline_config=pipeline_config,
        )

        # Store run_id for later retrieval
        run_id = orchestrator.run_id

        # Run pipeline (async)
        stats = asyncio.run(orchestrator.run())

        # Display comprehensive results
        _display_pipeline_results(db, run_id, stats)

        click.echo("\nPipeline completed successfully!")

    except KeyboardInterrupt:
        click.echo("\nPipeline interrupted by user.", err=True)
        raise click.Abort()

    except Exception as e:
        click.echo(f"\nPipeline failed: {e}", err=True)
        raise click.Abort()

    finally:
        db.close()


def _display_pipeline_results(db: DatabaseConnection, run_id: str, stats: dict) -> None:
    """Display comprehensive pipeline results including costs.

    Args:
        db: Database connection.
        run_id: Pipeline run ID.
        stats: Basic statistics from pipeline.
    """
    conn = db.connect()

    click.echo("\nPipeline Results:")
    click.echo("=" * 70)

    # Article processing statistics
    click.echo("\nArticle Processing:")
    if stats.get("collected", 0) > 0:
        click.echo(f"  Collected:     {stats['collected']:>6} articles")

    if stats.get("filtered", 0) > 0:
        click.echo(f"  Filtered:      {stats['filtered']:>6} articles")
        matched = stats.get("matched", 0)
        rejected = stats.get("rejected", 0)
        match_rate = (matched / stats['filtered'] * 100) if stats['filtered'] > 0 else 0
        click.echo(f"    - Matched:   {matched:>6} ({match_rate:.1f}%)")
        click.echo(f"    - Rejected:  {rejected:>6} ({100-match_rate:.1f}%)")

    if stats.get("scraped", 0) > 0:
        click.echo(f"  Scraped:       {stats['scraped']:>6} articles")

    if stats.get("deduplicated", 0) > 0:
        dedup = stats['deduplicated']
        dupes = stats.get("duplicates_found", 0)
        click.echo(f"  Deduplicated:  {dedup:>6} articles checked ({dupes} duplicates found)")

    if stats.get("summarized", 0) > 0:
        click.echo(f"  Summarized:    {stats['summarized']:>6} articles")

    if stats.get("digested", 0) > 0:
        click.echo(f"  Digested:      {stats['digested']:>6} digest(s) generated")

    # API costs and tokens
    click.echo("\nAPI Usage & Costs:")

    # Get total cost and tokens from pipeline_runs
    run_result = conn.execute(
        """
        SELECT total_cost, total_tokens, duration_seconds
        FROM pipeline_runs
        WHERE run_id = ?
        """,
        (run_id,)
    )
    run_row = run_result.fetchone()

    if run_row:
        total_cost, total_tokens, duration = run_row

        if total_cost and total_cost > 0:
            click.echo(f"  Total Cost:    ${total_cost:>8.4f}")
            click.echo(f"  Total Tokens:  {total_tokens:>9,}")

            # Cost breakdown by provider (extract from model name)
            provider_result = conn.execute(
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
                (run_id,)
            )
            provider_rows = provider_result.fetchall()

            if provider_rows:
                click.echo("\n  By Provider:")
                for provider, cost, tokens, calls in provider_rows:
                    pct = (cost / total_cost * 100) if total_cost > 0 else 0
                    click.echo(f"    {provider:<10} ${cost:>8.4f} ({pct:>5.1f}%)  |  {tokens:>9,} tokens  |  {calls:>4} calls")

            # Cost breakdown by module
            module_result = conn.execute(
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
                (run_id,)
            )
            module_rows = module_result.fetchall()

            if module_rows:
                click.echo("\n  By Module:")
                for module, cost, tokens, calls in module_rows:
                    pct = (cost / total_cost * 100) if total_cost > 0 else 0
                    click.echo(f"    {module:<15} ${cost:>8.4f} ({pct:>5.1f}%)  |  {tokens:>9,} tokens  |  {calls:>4} calls")

        # Duration
        if duration:
            minutes = int(duration // 60)
            seconds = duration % 60
            click.echo(f"\n  Duration:      {minutes}m {seconds:.1f}s")

    # Cache performance (for this run, we approximate from today's cache stats)
    cache_result = conn.execute(
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
        click.echo("\nCache Performance (Today):")
        for cache_type, requests, hits, misses, hit_rate, api_saved, cost_saved in cache_rows:
            if requests > 0:
                click.echo(f"  {cache_type.capitalize():<15} Hit Rate: {hit_rate:>5.1f}%  |  {hits}/{requests} hits  |  ${cost_saved:>7.4f} saved")

    click.echo("=" * 70)


def _reset_articles(db: DatabaseConnection, reset_type: str) -> None:
    """Reset articles to allow reprocessing.

    Args:
        db: Database connection.
        reset_type: Type of reset (summarization, digest, all).
    """
    conn = db.connect()

    if reset_type == "digest":
        # Reset digested articles to summarized
        result = conn.execute(
            """
            UPDATE articles
            SET pipeline_stage = 'summarized',
                included_in_digest = FALSE,
                digest_version = NULL
            WHERE pipeline_stage = 'digested' OR included_in_digest = TRUE
            """
        )
        # Also clear digest records for today
        from datetime import date

        conn.execute("DELETE FROM digests WHERE digest_date = ?", (date.today().isoformat(),))
        conn.commit()
        click.echo(f"Reset {result.rowcount} articles for re-digesting")

    elif reset_type == "summarization":
        # Reset summarized/digested articles back to scraped
        result = conn.execute(
            """
            UPDATE articles
            SET pipeline_stage = 'scraped',
                processing_status = 'completed',
                summary = NULL,
                summary_title = NULL,
                key_points = NULL,
                entities = NULL,
                summarized_at = NULL,
                included_in_digest = FALSE,
                digest_version = NULL
            WHERE pipeline_stage IN ('summarized', 'digested')
            """
        )
        conn.commit()
        click.echo(f"Reset {result.rowcount} articles for re-summarization")

    elif reset_type == "all":
        # Reset all articles to collected stage
        result = conn.execute(
            """
            UPDATE articles
            SET pipeline_stage = 'collected',
                processing_status = 'pending',
                is_match = NULL,
                classification_reason = NULL,
                confidence = NULL,
                topic = NULL,
                filtered_at = NULL,
                content = NULL,
                author = NULL,
                content_length = NULL,
                extraction_method = NULL,
                extraction_quality = NULL,
                scraped_at = NULL,
                summary = NULL,
                summary_title = NULL,
                key_points = NULL,
                entities = NULL,
                summarized_at = NULL,
                included_in_digest = FALSE,
                digest_version = NULL
            """
        )
        conn.commit()
        click.echo(f"Reset {result.rowcount} articles for full reprocessing")
