"""HTML email formatter for digest emails."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


class HtmlEmailFormatter:
    """Formats news digests as Outlook-compatible HTML emails.

    Uses Jinja2 templates with table-based layouts for compatibility
    with Outlook's Word-based rendering engine.
    """

    def __init__(self) -> None:
        """Initialize the formatter with Jinja2 environment."""
        templates_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def format(self, digest_data: Dict[str, Any]) -> str:
        """Format digest data as HTML email.

        Args:
            digest_data: Dictionary from DigestRepository.get_digest_by_date()
                containing markdown_output, meta_analysis_json, article_count, etc.

        Returns:
            HTML string formatted for Outlook email.
        """
        logger.debug(
            "formatting_digest",
            date=digest_data.get("digest_date"),
            article_count=digest_data.get("article_count"),
        )

        # Parse meta-analysis JSON
        meta_analysis = self._parse_meta_analysis(digest_data.get("meta_analysis_json"))

        # Format date in German style
        digest_date = self._format_date(digest_data.get("digest_date"))

        # Get template and render
        template = self.env.get_template("email_digest.html")
        html = template.render(
            date=digest_date,
            article_count=digest_data.get("article_count", 0),
            key_themes=meta_analysis.get("key_themes", []),
            credit_risk_signals=meta_analysis.get("credit_risk_signals", []),
            regulatory_updates=meta_analysis.get("regulatory_updates", []),
            market_insights=meta_analysis.get("market_insights", []),
            markdown_content=self._markdown_to_html(digest_data.get("markdown_output", "")),
            version=digest_data.get("version", 1),
            generated_at=digest_data.get("generated_at", ""),
        )

        logger.debug("digest_formatted", html_length=len(html))
        return html

    def _parse_meta_analysis(self, meta_json: str | None) -> Dict[str, List[str]]:
        """Parse meta-analysis JSON string.

        Args:
            meta_json: JSON string containing meta-analysis data.

        Returns:
            Dictionary with key_themes, credit_risk_signals, etc.
        """
        if not meta_json:
            return {}

        try:
            return json.loads(meta_json)
        except json.JSONDecodeError as e:
            logger.warning("meta_analysis_parse_failed", error=str(e))
            return {}

    def _format_date(self, date_str: str | None) -> str:
        """Format date string in German style.

        Args:
            date_str: ISO format date string (YYYY-MM-DD).

        Returns:
            German formatted date (e.g., "6. Januar 2026").
        """
        if not date_str:
            return datetime.now().strftime("%d. %B %Y")

        german_months = {
            1: "Januar",
            2: "Februar",
            3: "März",
            4: "April",
            5: "Mai",
            6: "Juni",
            7: "Juli",
            8: "August",
            9: "September",
            10: "Oktober",
            11: "November",
            12: "Dezember",
        }

        try:
            dt = datetime.fromisoformat(date_str)
            day = dt.day
            month = german_months.get(dt.month, dt.strftime("%B"))
            year = dt.year
            return f"{day}. {month} {year}"
        except (ValueError, TypeError):
            return date_str

    def _markdown_to_html(self, md_content: str) -> str:
        """Convert markdown content to HTML.

        Args:
            md_content: Markdown formatted string.

        Returns:
            HTML formatted string.
        """
        if not md_content:
            return ""

        try:
            # Convert markdown to HTML with common extensions
            html = markdown.markdown(
                md_content,
                extensions=["tables", "nl2br"],
            )
            return html
        except Exception as e:
            logger.warning("markdown_conversion_failed", error=str(e))
            # Return escaped plain text as fallback
            return f"<pre>{md_content}</pre>"
