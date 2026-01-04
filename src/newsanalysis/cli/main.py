"""Command-line interface for NewsAnalysis."""

import click

from newsanalysis.__version__ import __version__
from newsanalysis.cli.commands import cost_report, export, health, run, stats


@click.group()
@click.version_option(version=__version__, prog_name="newsanalysis")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """NewsAnalysis - AI-powered Swiss news intelligence for credit risk.

    A cost-optimized system for automated collection, filtering, and analysis
    of Swiss business news, delivering actionable credit risk insights.
    """
    ctx.ensure_object(dict)


# Register commands
cli.add_command(run)
cli.add_command(export)
cli.add_command(stats)
cli.add_command(cost_report)
cli.add_command(health)


def main() -> None:
    """Main entry point for CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
