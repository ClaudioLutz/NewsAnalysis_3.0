"""Email digest command."""

from datetime import date
from typing import Optional

import click

from newsanalysis.core.config import Config
from newsanalysis.database.connection import DatabaseConnection
from newsanalysis.database.digest_repository import DigestRepository
from newsanalysis.services.digest_formatter import HtmlEmailFormatter
from newsanalysis.services.email_service import OutlookEmailService
from newsanalysis.utils.logging import setup_logging


@click.command()
@click.option(
    "--preview",
    "-p",
    is_flag=True,
    help="Open email in Outlook without sending",
)
@click.option(
    "--date",
    "digest_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Date of digest to send (YYYY-MM-DD, defaults to today)",
)
@click.option(
    "--recipient",
    "-r",
    type=str,
    default=None,
    help="Override recipient email address",
)
def email(
    preview: bool,
    digest_date: Optional[date],
    recipient: Optional[str],
) -> None:
    """Send the news digest email via Outlook.

    Retrieves the latest digest for the specified date (or today) from the
    database, formats it as HTML, and sends it via Outlook COM automation.

    Examples:
        newsanalysis email                      # Send today's digest
        newsanalysis email --preview            # Preview without sending
        newsanalysis email --date 2026-01-05    # Send specific date's digest
        newsanalysis email -r other@example.com # Override recipient
    """
    # Load configuration
    try:
        config = Config()  # type: ignore
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        click.echo("Please ensure .env file exists with required settings.", err=True)
        raise click.Abort()

    # Setup logging
    setup_logging(log_level=config.log_level, log_format=config.log_format)

    # Determine recipient
    email_recipient = recipient or config.email_recipient
    if not email_recipient:
        click.echo("Error: No recipient specified.", err=True)
        click.echo(
            "Set EMAIL_RECIPIENT in .env or use --recipient option.",
            err=True,
        )
        raise click.Abort()

    # Determine date
    target_date = digest_date.date() if digest_date else date.today()

    # Validate date is not in the future
    if target_date > date.today():
        click.echo(f"Error: Cannot send digest for future date {target_date}.", err=True)
        raise click.Abort()

    click.echo("NewsAnalysis Email Digest")
    click.echo("=" * 50)
    click.echo(f"Date: {target_date}")
    click.echo(f"Recipient: {email_recipient}")
    click.echo(f"Mode: {'Preview' if preview else 'Send'}")
    click.echo("=" * 50)

    # Check Outlook availability first
    with OutlookEmailService() as email_service:
        if not email_service.is_available():
            click.echo("\nError: Outlook automation not available.", err=True)
            click.echo(
                "Ensure you're on Windows with Outlook and pywin32 installed.",
                err=True,
            )
            raise click.Abort()

        # Initialize database and repository
        db = DatabaseConnection(config.db_path)
        try:
            repo = DigestRepository(db)

            # Get digest for date
            click.echo(f"\nFetching digest for {target_date}...")
            digest_data = repo.get_digest_by_date(target_date)

            if not digest_data:
                click.echo(f"\nError: No digest found for {target_date}.", err=True)
                click.echo("Run 'newsanalysis run' first to generate a digest.", err=True)
                raise click.Abort()

            click.echo(
                f"Found digest v{digest_data['version']} with "
                f"{digest_data['article_count']} articles"
            )

            # Format as HTML
            click.echo("Formatting email...")
            formatter = HtmlEmailFormatter()
            html_body = formatter.format(digest_data)

            # Create subject line
            try:
                subject = config.email_subject_template.format(
                    date=target_date.strftime("%d.%m.%Y"),
                    count=digest_data["article_count"],
                )
            except KeyError as e:
                click.echo(
                    f"Warning: Invalid email_subject_template - missing {e}. Using default.",
                    err=True,
                )
                subject = f"Bonitäts-News: {target_date.strftime('%d.%m.%Y')} - {digest_data['article_count']} relevante Artikel"

            # Send or preview
            if preview:
                click.echo("\nOpening email in Outlook for preview...")
            else:
                click.echo("\nSending email...")

            result = email_service.send_html_email(
                to=email_recipient,
                subject=subject,
                html_body=html_body,
                preview=preview,
            )

            if result.success:
                click.echo(f"\n{result.message}")
            else:
                click.echo(f"\nError: {result.message}", err=True)
                raise click.Abort()

        finally:
            db.close()
