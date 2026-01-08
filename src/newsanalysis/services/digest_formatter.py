"""HTML email formatter for digest emails."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from newsanalysis.pipeline.formatters.german_formatter import TOPIC_PRIORITY, TOPIC_TRANSLATIONS
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
                containing json_output, meta_analysis_json, article_count, etc.

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

        # Filter out "Analysis unavailable" placeholders
        for key in ["key_themes", "credit_risk_signals", "regulatory_updates", "market_insights"]:
            if key in meta_analysis:
                meta_analysis[key] = [
                    item for item in meta_analysis[key]
                    if item and "unavailable" not in item.lower()
                ]

        # Parse articles from JSON output grouped by topic
        articles_by_topic = self._parse_articles(digest_data.get("json_output"))

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
            articles_by_topic=articles_by_topic,
            topic_translations=TOPIC_TRANSLATIONS,
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

    def _parse_articles(self, json_output: Optional[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Parse articles from JSON output and group by topic.

        Args:
            json_output: Full JSON digest output string.

        Returns:
            Dictionary mapping topic to list of article dicts, ordered by TOPIC_PRIORITY.
        """
        if not json_output:
            return {}

        try:
            data = json.loads(json_output)
            articles = data.get("articles", [])

            # Group by topic (unknown topics fall through to "other")
            articles_by_topic: Dict[str, List[Dict[str, Any]]] = {}
            for article in articles:
                topic = article.get("topic", "other")
                # Fallback unknown topics to "other" to prevent article loss
                if topic not in TOPIC_PRIORITY:
                    logger.warning("unknown_topic_fallback", topic=topic)
                    topic = "other"

                if topic not in articles_by_topic:
                    articles_by_topic[topic] = []

                # Smart truncate summary at sentence boundary
                summary = self._truncate_summary(article.get("summary", ""))

                articles_by_topic[topic].append({
                    "title": article.get("title", "Untitled"),
                    "url": article.get("url", ""),
                    "source": article.get("source", ""),
                    "summary": summary,
                    "key_points": article.get("key_points", [])[:2],
                    "topic": topic,
                    "confidence": article.get("confidence", 0),
                })

            # Sort articles within each topic by confidence (descending)
            for topic in articles_by_topic:
                articles_by_topic[topic].sort(
                    key=lambda a: a.get("confidence", 0),
                    reverse=True
                )

            # Order topics by priority, filter empty topics
            sorted_by_topic = {
                t: articles_by_topic[t]
                for t in TOPIC_PRIORITY
                if t in articles_by_topic and articles_by_topic[t]
            }

            return sorted_by_topic

        except json.JSONDecodeError as e:
            logger.warning("json_output_parse_failed", error=str(e))
            return {}

    def _truncate_summary(self, summary: str, max_length: int = 200) -> str:
        """Smart truncate summary at sentence boundary.

        Args:
            summary: Original summary text.
            max_length: Maximum length before truncation.

        Returns:
            Truncated summary, preferring sentence boundaries.
        """
        if not summary or len(summary) <= max_length:
            return summary

        # Try to cut at first sentence within max_length
        first_sentence_end = summary.find(". ")
        if 0 < first_sentence_end < max_length:
            return summary[:first_sentence_end + 1]

        # Otherwise cut at word boundary
        truncated = summary[:max_length - 3]
        last_space = truncated.rfind(" ")
        if last_space > max_length // 2:
            return truncated[:last_space] + "..."
        return truncated + "..."

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

