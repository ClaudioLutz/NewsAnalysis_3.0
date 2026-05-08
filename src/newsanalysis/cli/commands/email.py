"""Email digest command."""

import json
from datetime import date
from typing import Any, Dict, Optional

import click

from newsanalysis.core.config import Config
from newsanalysis.database.connection import DatabaseConnection
from newsanalysis.database.digest_repository import DigestRepository
from newsanalysis.database.repository import ArticleRepository
from newsanalysis.services.company_matcher import CompanyMatcher
from newsanalysis.services.company_matcher import CompanyMatcher
from newsanalysis.services.digest_formatter import HtmlEmailFormatter
from newsanalysis.services.email_service import OutlookEmailService
from newsanalysis.utils.logging import setup_logging


def _filter_today_articles(digest_data: Dict[str, Any], target_date: date) -> Dict[str, Any]:
    """Filter digest articles to only include those published on target date.

    Args:
        digest_data: The digest data dictionary from the repository.
        target_date: The date to filter articles by.

    Returns:
        Modified digest_data with only today's articles.
    """
    json_output = digest_data.get("json_output")
    if not json_output:
        return digest_data

    try:
        data = json.loads(json_output)
    except (json.JSONDecodeError, TypeError):
        return digest_data

    # Get articles list from the digest structure
    articles = data.get("articles", [])
    if not articles:
        return digest_data

    # Filter articles by published_at date
    target_str = target_date.isoformat()
    filtered_articles = []

    for article in articles:
        published_at = article.get("published_at", "")
        # Check if published_at starts with target date (handles datetime strings)
        if published_at and published_at.startswith(target_str):
            filtered_articles.append(article)

    # Update the articles in the data structure
    data["articles"] = filtered_articles

    # Update digest data with filtered articles
    result = dict(digest_data)
    result["json_output"] = json.dumps(data)
    result["article_count"] = len(filtered_articles)

    return result


@click.command()
@click.option(
    "--mode",
    "-m",
    "delivery_mode_override",
    type=click.Choice(["send", "preview", "draft"], case_sensitive=False),
    default=None,
    help=(
        "Delivery mode: 'send' (immediate), 'preview' (open in Outlook so you "
        "click Send yourself), or 'draft' (save to Outlook Drafts folder). "
        "Defaults to EMAIL_DELIVERY_MODE from .env."
    ),
)
@click.option(
    "--preview",
    "-p",
    is_flag=True,
    help="Shortcut for --mode preview",
)
@click.option(
    "--draft",
    is_flag=True,
    help="Shortcut for --mode draft",
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
@click.option(
    "--today-only",
    is_flag=True,
    default=False,
    help="Only include articles published today in the digest",
)
def email(
    delivery_mode_override: Optional[str],
    preview: bool,
    draft: bool,
    digest_date: Optional[date],
    recipient: Optional[str],
    today_only: bool,
) -> None:
    """Send the news digest email via Outlook.

    Retrieves the latest digest for the specified date (or today) from the
    database, formats it as HTML, and sends it via Outlook COM automation.

    Examples:
        newsanalysis email                      # Send today's digest (uses EMAIL_DELIVERY_MODE)
        newsanalysis email --preview            # Open in Outlook to review and click Send
        newsanalysis email --draft              # Save to Outlook Drafts folder
        newsanalysis email --mode draft         # Same as --draft, explicit form
        newsanalysis email --date 2026-01-05    # Send specific date's digest
        newsanalysis email -r other@example.com # Override recipient
    """
    # Resolve mutually exclusive shortcut flags
    explicit_modes = [
        m for m, used in (
            (delivery_mode_override.lower() if delivery_mode_override else None, bool(delivery_mode_override)),
            ("preview", preview),
            ("draft", draft),
        ) if used
    ]
    if len(explicit_modes) > 1:
        click.echo(
            "Error: --mode, --preview and --draft are mutually exclusive. Use only one.",
            err=True,
        )
        raise click.Abort()

    # Load configuration
    try:
        config = Config()  # type: ignore
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        click.echo("Please ensure .env file exists with required settings.", err=True)
        raise click.Abort()

    # Resolve final delivery mode: CLI override > config default
    delivery_mode = explicit_modes[0] if explicit_modes else config.email_delivery_mode

    # Setup logging
    setup_logging(log_level=config.log_level, log_dir=config.log_dir)

    # Determine recipients
    if recipient:
        # Command line override - single recipient
        email_recipients = [recipient]
    else:
        # Use configured recipients
        email_recipients = config.email_recipient_list

    if not email_recipients:
        click.echo("Error: No recipients specified.", err=True)
        click.echo(
            "Set EMAIL_RECIPIENTS in .env or use --recipient option.",
            err=True,
        )
        raise click.Abort()

    recipients_display = ", ".join(email_recipients)

    # Determine date
    target_date = digest_date.date() if digest_date else date.today()

    # Validate date is not in the future
    if target_date > date.today():
        click.echo(f"Error: Cannot send digest for future date {target_date}.", err=True)
        raise click.Abort()

    click.echo("NewsAnalysis Email Digest")
    click.echo("=" * 50)
    click.echo(f"Date: {target_date}")
    click.echo(f"Recipients: {recipients_display}")
    mode_label = {"send": "Send", "preview": "Preview", "draft": "Draft"}[delivery_mode]
    click.echo(f"Mode: {mode_label}")
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
            article_repo = ArticleRepository(db)

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

            # Filter to today's articles if requested
            if today_only:
                digest_data = _filter_today_articles(digest_data, target_date)
                click.echo(
                    f"Filtered to {digest_data['article_count']} articles from today"
                )

            # Initialize company matcher for crediweb links (optional)
            company_matcher = None
            if config.db_server and config.db_database:
                company_matcher = CompanyMatcher(
                    db_server=config.db_server,
                    db_database=config.db_database,
                    db_driver=config.db_driver,
                )
                company_matcher.connect()

            # Format as HTML with embedded images
            click.echo("Formatting email with images...")
            formatter = HtmlEmailFormatter(
                article_repository=article_repo,
                company_matcher=company_matcher,
            )
            html_body, image_cid_mapping = formatter.format_with_images(
                digest_data,
                include_images=True
            )

            if company_matcher is not None:
                company_matcher.close()

            click.echo(f"Prepared {len(image_cid_mapping)} images for embedding")

            # Create dynamic subject line with top article title
            top_title = formatter.get_top_article_title(digest_data, max_length=50)

            if top_title:
                subject = f"Creditreform News-Digest: {top_title}"
            else:
                # Fallback to date-based subject when no articles
                subject = f"Creditreform News-Digest: {target_date.strftime('%d.%m.%Y')}"

            # Email 1: VIP group (all recipients in TO, they see each other)
            action_msg = {
                "send": "Sending VIP group email...",
                "preview": "Opening VIP group email in Outlook for preview...",
                "draft": "Saving VIP group email to Outlook Drafts...",
            }[delivery_mode]
            click.echo(f"\n{action_msg}")

            result = email_service.send_html_email_with_images(
                to=email_recipients,
                subject=subject,
                html_body=html_body,
                image_attachments=image_cid_mapping,
                delivery_mode=delivery_mode,
            )

            if result.success:
                click.echo(f"\n{result.message}")
            else:
                click.echo(f"\nError: {result.message}", err=True)
                raise click.Abort()

            # Email 2+: Individual emails to remaining recipients
            # Each gets their own email — cannot see VIP group or each other.
            bcc_recipients = config.email_bcc_list
            if bcc_recipients and not recipient:
                bcc_action = {
                    "send": "Sending",
                    "preview": "Opening",
                    "draft": "Drafting",
                }[delivery_mode]
                click.echo(
                    f"\n{bcc_action} individual emails to {len(bcc_recipients)} recipients..."
                )
                done_verb = {"send": "Sent", "preview": "Opened", "draft": "Drafted"}[delivery_mode]
                for bcc_addr in bcc_recipients:
                    bcc_result = email_service.send_html_email_with_images(
                        to=bcc_addr,
                        subject=subject,
                        html_body=html_body,
                        image_attachments=image_cid_mapping,
                        delivery_mode=delivery_mode,
                    )
                    if bcc_result.success:
                        click.echo(f"  {done_verb} for {bcc_addr}")
                    else:
                        click.echo(f"\n  Warning: Failed for {bcc_addr}: {bcc_result.message}", err=True)

        finally:
            db.close()
