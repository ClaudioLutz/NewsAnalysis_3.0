"""Cost reporting command for monitoring API costs and cache performance."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click

from newsanalysis.core.config import Config
from newsanalysis.database.connection import DatabaseConnection
from newsanalysis.services.cache_service import CacheService
from newsanalysis.utils.date_utils import now_utc


@click.command(name="cost-report")
@click.option(
    "--period",
    type=click.Choice(["today", "week", "month", "all"], case_sensitive=False),
    default="week",
    help="Time period for cost report (default: week)",
)
@click.option(
    "--detailed",
    is_flag=True,
    help="Show detailed breakdown by module and date",
)
@click.option(
    "--cache-only",
    is_flag=True,
    help="Show only cache statistics",
)
def cost_report_command(period: str, detailed: bool, cache_only: bool):
    """Generate cost report with API usage and cache statistics.

    Shows:
    - Total API costs for the selected period
    - Cost breakdown by module (filter, summarizer, digest)
    - Cache hit rates and cost savings
    - Budget utilization
    - Optimization recommendations
    """
    try:
        # Load configuration
        config = Config()

        # Get database path
        db_path = Path(config.database_path)
        if not db_path.exists():
            click.echo(click.style("Error: Database not found. Run 'newsanalysis run' first.", fg="red"))
            return 1

        # Connect to database
        db = DatabaseConnection(str(db_path))

        # Initialize cache service for cache stats
        cache_service = CacheService(db.conn)

        # Calculate date range
        end_date = now_utc()
        if period == "today":
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            period_name = "Today"
        elif period == "week":
            start_date = end_date - timedelta(days=7)
            period_name = "Last 7 Days"
        elif period == "month":
            start_date = end_date - timedelta(days=30)
            period_name = "Last 30 Days"
        else:  # all
            start_date = datetime(2000, 1, 1)  # Far past
            period_name = "All Time"

        # Display header
        click.echo()
        click.echo(click.style("=" * 70, fg="cyan"))
        click.echo(click.style(f"Cost Report - {period_name}", fg="cyan", bold=True))
        click.echo(click.style("=" * 70, fg="cyan"))
        click.echo()

        if not cache_only:
            # Get API cost statistics
            api_stats = _get_api_cost_stats(db.conn, start_date, end_date)
            _display_api_costs(api_stats, config.daily_cost_limit, detailed)

        # Get cache statistics
        cache_stats = _get_cache_statistics(cache_service, db.conn, start_date, end_date)
        _display_cache_stats(cache_stats)

        if not cache_only:
            # Show optimization recommendations
            _display_recommendations(api_stats, cache_stats, config)

        click.echo()
        db.close()
        return 0

    except Exception as e:
        click.echo(click.style(f"Error generating cost report: {e}", fg="red"))
        return 1


def _get_api_cost_stats(conn: sqlite3.Connection, start_date: datetime, end_date: datetime) -> dict:
    """Get API cost statistics from database."""
    cursor = conn.cursor()

    # Total costs by module
    cursor.execute(
        """
        SELECT
            module,
            COUNT(*) as calls,
            SUM(input_tokens) as input_tokens,
            SUM(output_tokens) as output_tokens,
            SUM(total_tokens) as total_tokens,
            SUM(cost) as total_cost
        FROM api_calls
        WHERE created_at BETWEEN ? AND ?
        GROUP BY module
        ORDER BY total_cost DESC
        """,
        (start_date.isoformat(), end_date.isoformat()),
    )

    by_module = []
    total_cost = 0.0
    total_calls = 0
    total_tokens = 0

    for row in cursor.fetchall():
        stats = {
            "module": row[0],
            "calls": row[1],
            "input_tokens": row[2],
            "output_tokens": row[3],
            "total_tokens": row[4],
            "cost": row[5],
        }
        by_module.append(stats)
        total_cost += row[5]
        total_calls += row[1]
        total_tokens += row[4]

    # Daily breakdown
    cursor.execute(
        """
        SELECT
            DATE(created_at) as date,
            COUNT(*) as calls,
            SUM(cost) as cost
        FROM api_calls
        WHERE created_at BETWEEN ? AND ?
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 30
        """,
        (start_date.isoformat(), end_date.isoformat()),
    )

    by_date = [
        {"date": row[0], "calls": row[1], "cost": row[2]}
        for row in cursor.fetchall()
    ]

    return {
        "total_cost": total_cost,
        "total_calls": total_calls,
        "total_tokens": total_tokens,
        "by_module": by_module,
        "by_date": by_date,
    }


def _get_cache_statistics(cache_service: CacheService, conn: sqlite3.Connection, start_date: datetime, end_date: datetime) -> dict:
    """Get cache performance statistics."""
    cursor = conn.cursor()

    # Get cache stats for period
    cursor.execute(
        """
        SELECT
            cache_type,
            SUM(requests) as requests,
            SUM(hits) as hits,
            SUM(misses) as misses,
            SUM(api_calls_saved) as api_calls_saved,
            SUM(cost_saved) as cost_saved
        FROM cache_stats
        WHERE date >= DATE(?)
        GROUP BY cache_type
        """,
        (start_date.date().isoformat(),),
    )

    cache_stats = {}
    for row in cursor.fetchall():
        cache_type = row[0]
        requests = row[1] or 0
        hits = row[2] or 0
        hit_rate = (hits / requests * 100) if requests > 0 else 0.0

        cache_stats[cache_type] = {
            "requests": requests,
            "hits": hits,
            "misses": row[3] or 0,
            "hit_rate": hit_rate,
            "api_calls_saved": row[4] or 0,
            "cost_saved": row[5] or 0.0,
        }

    # Get overall cache summary
    summary = cache_service.get_cache_summary()

    return {
        "by_type": cache_stats,
        "summary": summary,
    }


def _display_api_costs(stats: dict, daily_limit: float, detailed: bool):
    """Display API cost statistics."""
    click.echo(click.style("API Cost Summary", fg="yellow", bold=True))
    click.echo("-" * 70)

    if stats["total_cost"] == 0:
        click.echo("No API calls in selected period.")
        click.echo()
        return

    # Total summary
    click.echo(f"Total Cost:        ${stats['total_cost']:.4f}")
    click.echo(f"Total API Calls:   {stats['total_calls']:,}")
    click.echo(f"Total Tokens:      {stats['total_tokens']:,}")
    click.echo()

    # Budget utilization (for week/month)
    if daily_limit > 0:
        # Assume 7 days for week, 30 for month
        days = 7 if len(stats["by_date"]) <= 7 else 30
        budget = daily_limit * days
        utilization = (stats["total_cost"] / budget * 100) if budget > 0 else 0

        if utilization > 100:
            color = "red"
        elif utilization > 80:
            color = "yellow"
        else:
            color = "green"

        click.echo(f"Budget Utilization: {click.style(f'{utilization:.1f}%', fg=color)} (${stats['total_cost']:.4f} / ${budget:.2f})")
        click.echo()

    # Cost by module
    if stats["by_module"]:
        click.echo(click.style("Cost by Module:", fg="yellow"))
        click.echo()
        click.echo(f"{'Module':<20} {'Calls':>10} {'Tokens':>12} {'Cost':>10} {'%':>8}")
        click.echo("-" * 70)

        for module_stats in stats["by_module"]:
            pct = (module_stats["cost"] / stats["total_cost"] * 100) if stats["total_cost"] > 0 else 0
            click.echo(
                f"{module_stats['module']:<20} "
                f"{module_stats['calls']:>10,} "
                f"{module_stats['total_tokens']:>12,} "
                f"${module_stats['cost']:>9.4f} "
                f"{pct:>7.1f}%"
            )

        click.echo()

    # Daily breakdown (if detailed)
    if detailed and stats["by_date"]:
        click.echo(click.style("Daily Breakdown:", fg="yellow"))
        click.echo()
        click.echo(f"{'Date':<12} {'Calls':>8} {'Cost':>10}")
        click.echo("-" * 35)

        for day_stats in stats["by_date"]:
            click.echo(
                f"{day_stats['date']:<12} "
                f"{day_stats['calls']:>8,} "
                f"${day_stats['cost']:>9.4f}"
            )

        click.echo()


def _display_cache_stats(cache_stats: dict):
    """Display cache performance statistics."""
    click.echo(click.style("Cache Performance", fg="yellow", bold=True))
    click.echo("-" * 70)

    if not cache_stats["by_type"]:
        click.echo("No cache statistics available for selected period.")
        click.echo()
        return

    # Cache stats by type
    total_hits = 0
    total_misses = 0
    total_saved = 0.0

    for cache_type, stats in cache_stats["by_type"].items():
        total_hits += stats["hits"]
        total_misses += stats["misses"]
        total_saved += stats["cost_saved"]

        click.echo(f"{cache_type.capitalize()} Cache:")
        click.echo(f"  Requests:       {stats['requests']:,}")
        click.echo(f"  Hits:           {stats['hits']:,}")
        click.echo(f"  Misses:         {stats['misses']:,}")

        if stats["hit_rate"] >= 70:
            color = "green"
        elif stats["hit_rate"] >= 40:
            color = "yellow"
        else:
            color = "red"

        hit_rate_str = f"{stats['hit_rate']:.1f}%"
        click.echo(f"  Hit Rate:       {click.style(hit_rate_str, fg=color)}")
        click.echo(f"  API Calls Saved: {stats['api_calls_saved']:,}")
        click.echo(f"  Cost Saved:     ${stats['cost_saved']:.4f}")
        click.echo()

    # Total savings
    click.echo(click.style(f"Total Cost Saved: ${total_saved:.4f}", fg="green", bold=True))
    click.echo()

    # Cache size summary
    summary = cache_stats["summary"]
    click.echo(click.style("Cache Size:", fg="yellow"))
    click.echo(f"  Classification Cache: {summary['classification_cache']['entries']:,} entries")
    click.echo(f"  Content Cache:        {summary['content_cache']['entries']:,} entries")
    click.echo()


def _display_recommendations(api_stats: dict, cache_stats: dict, config: Config):
    """Display cost optimization recommendations."""
    click.echo(click.style("Optimization Recommendations", fg="yellow", bold=True))
    click.echo("-" * 70)

    recommendations = []

    # Check cache hit rates
    for cache_type, stats in cache_stats["by_type"].items():
        if stats["hit_rate"] < 40:
            recommendations.append(
                f"⚠  Low {cache_type} cache hit rate ({stats['hit_rate']:.1f}%). "
                f"Consider increasing cache TTL."
            )

    # Check if summarizer cost is high
    for module_stats in api_stats["by_module"]:
        if module_stats["module"] == "summarizer":
            pct = (module_stats["cost"] / api_stats["total_cost"] * 100) if api_stats["total_cost"] > 0 else 0
            if pct > 60:
                recommendations.append(
                    f"⚠  Summarization accounts for {pct:.1f}% of costs. "
                    f"Consider using Batch API for 50% savings."
                )

    # Check budget utilization
    if config.daily_cost_limit > 0:
        avg_daily = api_stats["total_cost"] / max(len(api_stats["by_date"]), 1)
        if avg_daily > config.daily_cost_limit:
            recommendations.append(
                f"⚠  Average daily cost (${avg_daily:.4f}) exceeds limit (${config.daily_cost_limit:.2f}). "
                f"Reduce article volume or increase limit."
            )

    if recommendations:
        for rec in recommendations:
            click.echo(rec)
    else:
        click.echo(click.style("✓ No issues found. Cost optimization is performing well!", fg="green"))

    click.echo()
