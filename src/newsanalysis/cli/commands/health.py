# src/newsanalysis/cli/commands/health.py
"""Health check command for system diagnostics."""

import sqlite3
import sys
from datetime import datetime, timedelta, UTC
from pathlib import Path

import click

from newsanalysis.core.config import Config
from newsanalysis.database.connection import DatabaseConnection
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


@click.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed health information",
)
def health(verbose: bool) -> None:
    """
    Check system health and display diagnostics.

    Performs comprehensive health checks including:
    - Configuration validation
    - Database connectivity
    - Recent pipeline runs
    - API quota status
    - Disk space
    - Cache performance
    """
    click.echo("NewsAnalysis Health Check")
    click.echo("=" * 50)
    click.echo()

    health_status = {
        "config": False,
        "database": False,
        "recent_runs": False,
        "api_quota": False,
        "disk_space": False,
    }

    try:
        # 1. Configuration Check
        click.echo("🔍 Checking configuration...")
        try:
            config = Config()

            # Check OpenAI API key
            if config.openai_api_key and len(config.openai_api_key) > 10:
                click.echo("  ✓ OpenAI API key configured")
            else:
                click.echo("  ✗ OpenAI API key missing or invalid", err=True)

            # Check paths
            db_path = Path(config.db_path)
            if db_path.exists():
                click.echo(f"  ✓ Database file exists: {db_path}")
            else:
                click.echo(f"  ⚠ Database file not found: {db_path}", err=True)

            output_dir = Path(config.output_dir)
            if output_dir.exists():
                click.echo(f"  ✓ Output directory exists: {output_dir}")
            else:
                click.echo(f"  ⚠ Output directory not found: {output_dir}", err=True)

            health_status["config"] = True

        except Exception as e:
            click.echo(f"  ✗ Configuration error: {e}", err=True)
            health_status["config"] = False

        click.echo()

        # 2. Database Check
        click.echo("🔍 Checking database...")
        try:
            config = Config()
            db = DatabaseConnection(config.db_path)

            # Test connection
            cursor = db.conn.execute("SELECT 1")
            cursor.fetchone()
            click.echo("  ✓ Database connection OK")

            # Check tables
            cursor = db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]
            expected_tables = [
                "articles",
                "api_calls",
                "pipeline_runs",
                "digests",
                "classification_cache",
                "content_fingerprints",
                "cache_stats",
            ]

            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                click.echo(f"  ⚠ Missing tables: {', '.join(missing_tables)}", err=True)
            else:
                click.echo(f"  ✓ All required tables present ({len(tables)} tables)")

            # Count records
            if verbose:
                cursor = db.conn.execute("SELECT COUNT(*) FROM articles")
                article_count = cursor.fetchone()[0]
                click.echo(f"    - Articles: {article_count:,}")

                cursor = db.conn.execute("SELECT COUNT(*) FROM api_calls")
                api_call_count = cursor.fetchone()[0]
                click.echo(f"    - API calls: {api_call_count:,}")

                cursor = db.conn.execute("SELECT COUNT(*) FROM pipeline_runs")
                run_count = cursor.fetchone()[0]
                click.echo(f"    - Pipeline runs: {run_count:,}")

            health_status["database"] = True
            db.close()

        except Exception as e:
            click.echo(f"  ✗ Database error: {e}", err=True)
            health_status["database"] = False

        click.echo()

        # 3. Recent Pipeline Runs
        click.echo("🔍 Checking recent pipeline runs...")
        try:
            config = Config()
            db = DatabaseConnection(config.db_path)

            # Get recent runs (last 7 days)
            cursor = db.conn.execute(
                """
                SELECT run_id, status, started_at, collected_count, filtered_count
                FROM pipeline_runs
                WHERE started_at > datetime('now', '-7 days')
                ORDER BY started_at DESC
                LIMIT 5
                """
            )
            recent_runs = cursor.fetchall()

            if recent_runs:
                click.echo(f"  ✓ Found {len(recent_runs)} recent run(s) (last 7 days)")
                if verbose:
                    for run in recent_runs:
                        run_id, status, started_at, collected, filtered = run
                        click.echo(
                            f"    - {started_at}: {status} "
                            f"(collected: {collected}, filtered: {filtered})"
                        )
                health_status["recent_runs"] = True
            else:
                click.echo("  ⚠ No pipeline runs in last 7 days", err=True)
                health_status["recent_runs"] = False

            db.close()

        except Exception as e:
            click.echo(f"  ✗ Error checking pipeline runs: {e}", err=True)
            health_status["recent_runs"] = False

        click.echo()

        # 4. API Quota Check
        click.echo("🔍 Checking API usage and quota...")
        try:
            config = Config()
            db = DatabaseConnection(config.db_path)

            # Get today's API costs
            cursor = db.conn.execute(
                """
                SELECT SUM(cost), COUNT(*)
                FROM api_calls
                WHERE created_at >= date('now')
                """
            )
            row = cursor.fetchone()
            today_cost = row[0] or 0.0
            today_calls = row[1] or 0

            daily_limit = config.daily_cost_limit
            usage_percent = (today_cost / daily_limit * 100) if daily_limit > 0 else 0

            click.echo(f"  Today's usage: ${today_cost:.4f} / ${daily_limit:.2f} ({usage_percent:.1f}%)")
            click.echo(f"  API calls today: {today_calls:,}")

            if usage_percent >= 90:
                click.echo("  ⚠ High API usage (>90% of daily limit)", err=True)
                health_status["api_quota"] = False
            else:
                click.echo("  ✓ API usage within limits")
                health_status["api_quota"] = True

            # Cache performance
            if verbose:
                click.echo()
                click.echo("  Cache Performance:")
                cursor = db.conn.execute(
                    """
                    SELECT cache_type, requests, hits,
                           ROUND(CAST(hits AS FLOAT) / requests * 100, 1) as hit_rate
                    FROM cache_stats
                    WHERE date = date('now')
                    """
                )
                cache_stats = cursor.fetchall()
                if cache_stats:
                    for cache_type, requests, hits, hit_rate in cache_stats:
                        click.echo(f"    - {cache_type}: {hit_rate}% hit rate ({hits}/{requests})")
                else:
                    click.echo("    - No cache stats for today")

            db.close()

        except Exception as e:
            click.echo(f"  ✗ Error checking API usage: {e}", err=True)
            health_status["api_quota"] = False

        click.echo()

        # 5. Disk Space Check
        click.echo("🔍 Checking disk space...")
        try:
            config = Config()
            db_path = Path(config.db_path)

            if db_path.exists():
                db_size = db_path.stat().st_size
                db_size_mb = db_size / 1024 / 1024

                click.echo(f"  Database size: {db_size_mb:.2f} MB")

                if db_size_mb > 1000:  # > 1 GB
                    click.echo("  ⚠ Large database size (>1 GB)", err=True)
                    click.echo("    Consider running maintenance: scripts/maintenance.sh")
                else:
                    click.echo("  ✓ Database size OK")

                health_status["disk_space"] = True
            else:
                click.echo("  ⚠ Database file not found", err=True)
                health_status["disk_space"] = False

        except Exception as e:
            click.echo(f"  ✗ Error checking disk space: {e}", err=True)
            health_status["disk_space"] = False

        click.echo()

        # Overall Status
        click.echo("=" * 50)
        all_healthy = all(health_status.values())

        if all_healthy:
            click.echo("✅ Overall Status: HEALTHY")
            sys.exit(0)
        else:
            failed_checks = [k for k, v in health_status.items() if not v]
            click.echo(f"❌ Overall Status: UNHEALTHY")
            click.echo(f"   Failed checks: {', '.join(failed_checks)}")
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Health check failed: {e}", err=True)
        logger.exception("Health check error")
        sys.exit(1)
