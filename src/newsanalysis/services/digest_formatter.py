"""HTML email formatter for digest emails."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape

from newsanalysis.database.repository import ArticleRepository
from newsanalysis.pipeline.formatters.german_formatter import TOPIC_PRIORITY, TOPIC_TRANSLATIONS
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


class HtmlEmailFormatter:
    """Formats news digests as Outlook-compatible HTML emails.

    Uses Jinja2 templates with table-based layouts for compatibility
    with Outlook's Word-based rendering engine. Supports embedded images via CID.
    """

    def __init__(self, article_repository: Optional[ArticleRepository] = None) -> None:
        """Initialize the formatter with Jinja2 environment.

        Args:
            article_repository: Optional repository for fetching article images.
        """
        templates_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.article_repository = article_repository

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

                # Handle duplicate sources (grouped articles)
                duplicate_sources = article.get("duplicate_sources", [])
                all_sources = [article.get("source", "")]
                if duplicate_sources:
                    all_sources.extend([dup.get("source", "") for dup in duplicate_sources])
                # Filter out empty sources
                all_sources = [s for s in all_sources if s]

                articles_by_topic[topic].append({
                    "id": article.get("id"),  # Add article ID for image lookup
                    "title": article.get("title", "Untitled"),
                    "url": article.get("url", ""),
                    "source": article.get("source", ""),
                    "all_sources": all_sources,  # List of all sources including duplicates
                    "duplicate_sources": duplicate_sources,  # Full duplicate source info
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

    def format_with_images(
        self, digest_data: Dict[str, Any], include_images: bool = True
    ) -> Tuple[str, Dict[str, str]]:
        """Format digest data as HTML email with embedded images.

        Args:
            digest_data: Dictionary from DigestRepository.get_digest_by_date().
            include_images: Whether to include article images (default: True).

        Returns:
            Tuple of (html_body, image_attachments) where image_attachments
            maps CID to file path.
        """
        logger.debug(
            "formatting_digest_with_images",
            date=digest_data.get("digest_date"),
            article_count=digest_data.get("article_count"),
            include_images=include_images,
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

        # Fetch article images if repository available and images enabled
        image_cid_mapping: Dict[str, str] = {}
        if include_images and self.article_repository:
            image_cid_mapping = self._prepare_article_images(articles_by_topic)

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
            images_enabled=include_images,
        )

        logger.debug(
            "digest_with_images_formatted",
            html_length=len(html),
            image_count=len(image_cid_mapping),
        )

        return html, image_cid_mapping

    def _prepare_article_images(
        self, articles_by_topic: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, str]:
        """Prepare article images for CID embedding.

        Args:
            articles_by_topic: Dictionary mapping topic to article dicts.

        Returns:
            Dictionary mapping CID (e.g., "article_1_featured") to file path.
        """
        if not self.article_repository:
            return {}

        image_cid_mapping: Dict[str, str] = {}
        cid_counter = 0

        for topic, articles in articles_by_topic.items():
            for article in articles:
                article_id = article.get("id")

                if not article_id:
                    continue

                try:
                    # Fetch images for this article
                    images = self.article_repository.get_article_images(article_id)

                    if not images:
                        continue

                    # Get featured image first, or first image if no featured
                    featured_image = next(
                        (img for img in images if img.is_featured),
                        images[0] if images else None,
                    )

                    if featured_image and featured_image.local_path:
                        # Check if file exists
                        image_path = Path(featured_image.local_path)
                        if image_path.exists():
                            cid = f"article_{article_id}_img"
                            image_cid_mapping[cid] = str(image_path)

                            # Add CID reference to article dict for template
                            article["image_cid"] = cid

                            cid_counter += 1

                            logger.debug(
                                "article_image_prepared",
                                article_id=article_id,
                                cid=cid,
                                path=str(image_path),
                            )
                        else:
                            logger.warning(
                                "article_image_file_missing",
                                article_id=article_id,
                                path=str(featured_image.local_path),
                            )

                except Exception as e:
                    logger.warning(
                        "article_image_fetch_failed",
                        article_id=article_id,
                        error=str(e),
                    )
                    # Continue with other articles

        logger.info("article_images_prepared", total_images=cid_counter)

        return image_cid_mapping

