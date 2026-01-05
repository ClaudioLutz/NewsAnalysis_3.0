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
def run(
    limit: Optional[int],
    mode: str,
    skip_collection: bool,
    skip_filtering: bool,
    skip_scraping: bool,
    skip_summarization: bool,
    skip_digest: bool,
) -> None:
    """Run the news analysis pipeline.

    Examples:
        newsanalysis run                    # Run full pipeline
        newsanalysis run --limit 10         # Process only 10 articles
        newsanalysis run --mode express     # Quick mode
        newsanalysis run --skip-digest      # Skip digest generation
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
    setup_logging(log_level=config.log_level, log_format=config.log_format)

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

    try:
        # Create and run pipeline orchestrator
        orchestrator = PipelineOrchestrator(
            config=config,
            db=db,
            pipeline_config=pipeline_config,
        )

        # Run pipeline (async)
        stats = asyncio.run(orchestrator.run())

        # Display results
        click.echo("\nPipeline Results:")
        click.echo("=" * 50)

        if stats.get("collected", 0) > 0:
            click.echo(f"Articles collected: {stats['collected']}")

        if stats.get("filtered", 0) > 0:
            click.echo(f"Articles filtered: {stats['filtered']}")
            click.echo(f"  - Matched: {stats.get('matched', 0)}")
            click.echo(f"  - Rejected: {stats.get('rejected', 0)}")

        click.echo("=" * 50)
        click.echo("\nPipeline completed successfully!")

    except KeyboardInterrupt:
        click.echo("\nPipeline interrupted by user.", err=True)
        raise click.Abort()

    except Exception as e:
        click.echo(f"\nPipeline failed: {e}", err=True)
        raise click.Abort()

    finally:
        db.close()
