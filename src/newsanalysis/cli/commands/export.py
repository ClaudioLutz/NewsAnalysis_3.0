"""Export digest command."""

import asyncio
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import click

from newsanalysis.core.config import Config
from newsanalysis.database import DatabaseConnection, DigestRepository
from newsanalysis.pipeline.formatters import (
    GermanReportFormatter,
    JSONFormatter,
    MarkdownFormatter,
)
from newsanalysis.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


@click.command()
@click.option(
    "--date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Date of digest to export (default: today)",
)
@click.option(
    "--format",
    type=click.Choice(["json", "markdown", "german"]),
    default="markdown",
    help="Output format",
)
@click.option(
    "--output",
    type=click.Path(),
    default=None,
    help="Output file path (default: auto-generated)",
)
def export(
    date: Optional[date],
    format: str,
    output: Optional[str],
) -> None:
    """Export daily digest to file.

    Examples:
        newsanalysis export                         # Export today's digest
        newsanalysis export --date 2026-01-03       # Export specific date
        newsanalysis export --format json           # Export as JSON
    """
    # Load configuration
    try:
        config = Config()  # type: ignore
        config.validate_paths()
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        raise click.Abort()

    # Setup logging
    setup_logging(log_level=config.log_level, log_format=config.log_format, log_dir=config.log_dir)

    # Display configuration
    click.echo("NewsAnalysis Digest Export")
    click.echo("=" * 50)

    # Determine date
    if date:
        export_date = date.date()
    else:
        export_date = datetime.now().date()

    click.echo(f"Date: {export_date}")
    click.echo(f"Format: {format}")
    click.echo(f"Output: {output or 'Auto-generated'}")
    click.echo("=" * 50)

    # Run export
    try:
        asyncio.run(_export_digest(config, export_date, format, output))
    except KeyboardInterrupt:
        click.echo("\n\n⚠ Export cancelled by user")
        raise click.Abort()
    except Exception as e:
        click.echo(f"\n\n❌ Export failed: {e}", err=True)
        logger.error("export_failed", error=str(e))
        raise click.Abort()


async def _export_digest(
    config: Config, export_date: date, format: str, output_path: Optional[str]
) -> None:
    """Export digest implementation.

    Args:
        config: Configuration.
        export_date: Date to export.
        format: Output format.
        output_path: Output file path (optional).
    """
    click.echo("\n📊 Loading digest from database...")

    # Initialize database
    db = DatabaseConnection(config.database_path)
    digest_repo = DigestRepository(db)

    # Get digest from database
    digest_data = digest_repo.get_digest_by_date(export_date)

    if not digest_data:
        click.echo(f"\n❌ No digest found for {export_date}")
        click.echo("Run 'newsanalysis run' to generate a digest first.")
        return

    click.echo(f"✓ Found digest v{digest_data['version']} with {digest_data['article_count']} articles")

    # Get the appropriate output from database
    if format == "json":
        if digest_data["json_output"]:
            output_content = digest_data["json_output"]
            extension = "json"
        else:
            click.echo("⚠ JSON output not found in database, regenerating...")
            # Would need to regenerate - for now just error
            click.echo("❌ Cannot regenerate JSON output. Please run pipeline again.")
            return

    elif format == "markdown":
        if digest_data["markdown_output"]:
            output_content = digest_data["markdown_output"]
            extension = "md"
        else:
            click.echo("⚠ Markdown output not found in database, regenerating...")
            click.echo("❌ Cannot regenerate Markdown output. Please run pipeline again.")
            return

    elif format == "german":
        if digest_data["german_report"]:
            output_content = digest_data["german_report"]
            extension = "md"
        else:
            click.echo("⚠ German report not found in database, regenerating...")
            click.echo("❌ Cannot regenerate German report. Please run pipeline again.")
            return

    else:
        click.echo(f"❌ Unknown format: {format}")
        return

    # Determine output path
    if not output_path:
        # Auto-generate path
        filename = f"digest_{export_date}_{format}.{extension}"
        output_path = str(config.output_path / filename)

    # Write output
    click.echo(f"\n📝 Writing to: {output_path}")

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(output_content, encoding="utf-8")

    file_size = output_file.stat().st_size
    click.echo(f"✓ Exported {file_size:,} bytes")

    click.echo("\n✅ Export completed successfully!")
