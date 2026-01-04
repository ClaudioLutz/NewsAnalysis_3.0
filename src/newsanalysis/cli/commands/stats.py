"""Statistics command."""

from datetime import datetime, timedelta

import click

from newsanalysis.core.config import Config
from newsanalysis.database import DatabaseConnection
from newsanalysis.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


@click.command()
@click.option(
    "--period",
    type=click.Choice(["today", "week", "month", "all"]),
    default="week",
    help="Time period for statistics",
)
@click.option(
    "--detailed",
    is_flag=True,
    help="Show detailed statistics",
)
def stats(period: str, detailed: bool) -> None:
    """Show pipeline statistics and metrics.

    Examples:
        newsanalysis stats                  # Weekly statistics
        newsanalysis stats --period today   # Today's stats
        newsanalysis stats --detailed       # Detailed breakdown
    """
    # Load configuration
    try:
        config = Config()  # type: ignore
        config.validate_paths()
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        raise click.Abort()

    # Setup logging
    setup_logging(log_level=config.log_level, log_format=config.log_format)

    # Display configuration
    click.echo("NewsAnalysis Statistics")
    click.echo("=" * 50)
    click.echo(f"Period: {period}")
    click.echo("=" * 50)

    # Display statistics
    try:
        _display_stats(config, period, detailed)
    except Exception as e:
        click.echo(f"\n❌ Failed to load statistics: {e}", err=True)
        logger.error("stats_failed", error=str(e))
        raise click.Abort()


def _display_stats(config: Config, period: str, detailed: bool) -> None:
    """Display pipeline statistics.

    Args:
        config: Configuration.
        period: Time period.
        detailed: Show detailed stats.
    """
    # Initialize database
    db = DatabaseConnection(config.database_path)

    # Calculate date range
    now = datetime.now()
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_label = "Today"
    elif period == "week":
        start_date = now - timedelta(days=7)
        period_label = "Last 7 Days"
    elif period == "month":
        start_date = now - timedelta(days=30)
        period_label = "Last 30 Days"
    else:  # all
        start_date = datetime(2020, 1, 1)
        period_label = "All Time"

    click.echo(f"\n📊 {period_label} Statistics\n")

    # Article pipeline statistics
    click.echo("Pipeline Progress:")
    click.echo("-" * 50)

    stages = ["collected", "filtered", "scraped", "summarized", "digested"]
    for stage in stages:
        cursor = db.execute(
            """
            SELECT COUNT(*) FROM articles
            WHERE pipeline_stage = ?
            AND created_at >= ?
            """,
            (stage, start_date.isoformat()),
        )
        count = cursor.fetchone()[0]
        click.echo(f"  {stage.capitalize():<15} {count:>6}")

    # Match statistics
    click.echo("\nClassification Results:")
    click.echo("-" * 50)

    cursor = db.execute(
        """
        SELECT
            SUM(CASE WHEN is_match = 1 THEN 1 ELSE 0 END) as matched,
            SUM(CASE WHEN is_match = 0 THEN 1 ELSE 0 END) as rejected,
            AVG(CASE WHEN is_match = 1 THEN confidence END) as avg_confidence
        FROM articles
        WHERE filtered_at >= ?
        """,
        (start_date.isoformat(),),
    )

    row = cursor.fetchone()
    matched = row[0] or 0
    rejected = row[1] or 0
    avg_conf = row[2] or 0.0

    click.echo(f"  Matched:        {matched:>6}")
    click.echo(f"  Rejected:       {rejected:>6}")
    if matched > 0:
        click.echo(f"  Avg Confidence: {avg_conf:>6.1%}")

    # API costs
    click.echo("\nAPI Usage:")
    click.echo("-" * 50)

    cursor = db.execute(
        """
        SELECT
            COUNT(*) as calls,
            SUM(total_tokens) as tokens,
            SUM(cost) as total_cost
        FROM api_calls
        WHERE created_at >= ?
        """,
        (start_date.isoformat(),),
    )

    row = cursor.fetchone()
    calls = row[0] or 0
    tokens = row[1] or 0
    cost = row[2] or 0.0

    click.echo(f"  API Calls:      {calls:>6}")
    click.echo(f"  Total Tokens:   {tokens:>6,}")
    click.echo(f"  Total Cost:     ${cost:>6.2f}")

    # Pipeline runs
    click.echo("\nPipeline Runs:")
    click.echo("-" * 50)

    cursor = db.execute(
        """
        SELECT
            COUNT(*) as runs,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
            AVG(duration_seconds) as avg_duration
        FROM pipeline_runs
        WHERE started_at >= ?
        """,
        (start_date.isoformat(),),
    )

    row = cursor.fetchone()
    runs = row[0] or 0
    completed = row[1] or 0
    failed = row[2] or 0
    avg_duration = row[3] or 0.0

    click.echo(f"  Total Runs:     {runs:>6}")
    click.echo(f"  Completed:      {completed:>6}")
    click.echo(f"  Failed:         {failed:>6}")
    if avg_duration > 0:
        click.echo(f"  Avg Duration:   {avg_duration:>6.1f}s")

    # Digests
    click.echo("\nDigests Generated:")
    click.echo("-" * 50)

    cursor = db.execute(
        """
        SELECT COUNT(*) FROM digests
        WHERE generated_at >= ?
        """,
        (start_date.isoformat(),),
    )

    digest_count = cursor.fetchone()[0]
    click.echo(f"  Total Digests:  {digest_count:>6}")

    # Detailed stats
    if detailed:
        click.echo("\n\n📈 Detailed Statistics\n")

        # By source
        click.echo("Articles by Source:")
        click.echo("-" * 50)

        cursor = db.execute(
            """
            SELECT source, COUNT(*) as count
            FROM articles
            WHERE created_at >= ?
            GROUP BY source
            ORDER BY count DESC
            LIMIT 10
            """,
            (start_date.isoformat(),),
        )

        for row in cursor.fetchall():
            click.echo(f"  {row[0]:<20} {row[1]:>6}")

        # By topic
        click.echo("\nArticles by Topic:")
        click.echo("-" * 50)

        cursor = db.execute(
            """
            SELECT topic, COUNT(*) as count
            FROM articles
            WHERE topic IS NOT NULL
            AND created_at >= ?
            GROUP BY topic
            ORDER BY count DESC
            LIMIT 10
            """,
            (start_date.isoformat(),),
        )

        for row in cursor.fetchall():
            click.echo(f"  {row[0]:<30} {row[1]:>6}")

        # API costs by module
        click.echo("\nAPI Costs by Module:")
        click.echo("-" * 50)

        cursor = db.execute(
            """
            SELECT module, SUM(cost) as cost, COUNT(*) as calls
            FROM api_calls
            WHERE created_at >= ?
            GROUP BY module
            ORDER BY cost DESC
            """,
            (start_date.isoformat(),),
        )

        for row in cursor.fetchall():
            click.echo(f"  {row[0]:<20} ${row[1]:>8.2f} ({row[2]} calls)")

    click.echo("\n✅ Statistics loaded successfully")
