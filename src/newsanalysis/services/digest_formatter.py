"""HTML email formatter for digest emails."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape

from newsanalysis.database.repository import ArticleRepository
from newsanalysis.pipeline.formatters.german_formatter import (
    TOPIC_ICONS,
    TOPIC_PRIORITY,
    TOPIC_TRANSLATIONS,
)
from newsanalysis.services.company_matcher import CompanyMatcher
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)

# Logo paths (relative to project root)
SWISS_FLAG_PATH = Path(__file__).parent.parent.parent.parent / "docs" / "assets" / "swiss-flag.png"
SWISS_FLAG_CID = "swiss_flag"
PLACEHOLDER_PATH = Path(__file__).parent.parent.parent.parent / "docs" / "assets" / "placeholder-article.png"
PLACEHOLDER_CID = "placeholder_article"

# High-risk topics that should be visually emphasized
HIGH_RISK_TOPICS = {
    "insolvency_bankruptcy",
    "credit_risk",
    "business_scams",
    "ecommerce_fraud",
}

# Confidence threshold for elevated risk display
HIGH_CONFIDENCE_THRESHOLD = 0.85


class HtmlEmailFormatter:
    """Formats news digests as Outlook-compatible HTML emails.

    Uses Jinja2 templates with table-based layouts for compatibility
    with Outlook's Word-based rendering engine. Supports embedded images via CID.
    """

    def __init__(
        self,
        article_repository: Optional[ArticleRepository] = None,
        company_matcher: Optional[CompanyMatcher] = None,
    ) -> None:
        """Initialize the formatter with Jinja2 environment.

        Args:
            article_repository: Optional repository for fetching article images.
            company_matcher: Optional matcher for resolving company names to crediweb links.
        """
        templates_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.article_repository = article_repository
        self.company_matcher = company_matcher

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

        # Try dynamic LLM grouping first, fall back to static topics
        use_dynamic_groups = False
        group_icons: Dict[str, str] = {}
        article_groups = meta_analysis.get("article_groups", [])

        articles_by_topic = self._regroup_by_llm_groups(
            digest_data.get("json_output"), article_groups
        )
        if articles_by_topic:
            use_dynamic_groups = True
            group_icons = {g.get("label", ""): g.get("icon", "") for g in article_groups}
        else:
            articles_by_topic = self._parse_articles(digest_data.get("json_output"))

        # Format date in German style
        digest_date = self._format_date(digest_data.get("digest_date"))

        # Count credit impact distribution
        credit_impact_counts = self._count_credit_impacts(articles_by_topic)

        # Get template and render
        template = self.env.get_template("email_digest.html")
        html = template.render(
            date=digest_date,
            article_count=digest_data.get("article_count", 0),
            executive_summary=meta_analysis.get("executive_summary", []),
            key_themes=meta_analysis.get("key_themes", []),
            credit_risk_signals=meta_analysis.get("credit_risk_signals", []),
            regulatory_updates=meta_analysis.get("regulatory_updates", []),
            market_insights=meta_analysis.get("market_insights", []),
            articles_by_topic=articles_by_topic,
            topic_translations=TOPIC_TRANSLATIONS,
            topic_icons=TOPIC_ICONS,
            credit_impact_counts=credit_impact_counts,
            version=self._get_software_version(),
            generated_at=digest_data.get("generated_at", ""),
            use_dynamic_groups=use_dynamic_groups,
            group_icons=group_icons,
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

    def _parse_article_dict(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a single article from JSON into display format.

        Args:
            article: Raw article dict from JSON output.

        Returns:
            Processed article dict ready for template rendering.
        """
        topic = article.get("topic", "other")

        # Smart truncate summary at sentence boundary
        summary = self._truncate_summary(article.get("summary", ""))

        # Handle duplicate sources (grouped articles) with URLs
        duplicate_sources = article.get("duplicate_sources", [])
        source_links = []
        main_source = article.get("source", "")
        main_url = article.get("url", "")
        if main_source:
            source_links.append({"name": main_source, "url": main_url})
        if duplicate_sources:
            for dup in duplicate_sources:
                dup_source = dup.get("source", "")
                dup_url = dup.get("url", "")
                if dup_source:
                    source_links.append({"name": dup_source, "url": dup_url})
        all_sources = [s["name"] for s in source_links]

        # Extract company names from entities and resolve to crediweb links
        entities = article.get("entities", {})
        raw_companies = entities.get("companies", []) if entities else []
        if self.company_matcher and self.company_matcher.is_connected and raw_companies:
            companies = self.company_matcher.resolve_companies(raw_companies[:3])
        else:
            companies = [{"name": c, "url": ""} for c in raw_companies]

        # Determine credit impact (LLM value or rule-based fallback)
        confidence = article.get("confidence", 0)
        credit_impact = article.get("credit_impact") or self._determine_risk_level(
            topic, confidence
        )
        # Normalize old values to 3-level enum
        if credit_impact in ("elevated", "elevated_risk"):
            credit_impact = "negative"
        elif credit_impact == "standard":
            credit_impact = "neutral"

        # Extract relevance keywords from entities
        relevance_keywords = self._extract_relevance_keywords(entities, topic)

        # Neutral articles show 1 key point, others show 2
        max_key_points = 1 if credit_impact == "neutral" else 2

        return {
            "id": article.get("id"),
            "title": article.get("title", "Untitled"),
            "url": article.get("url", ""),
            "source": article.get("source", ""),
            "all_sources": all_sources,
            "source_links": source_links,
            "duplicate_sources": duplicate_sources,
            "summary": summary,
            "key_points": article.get("key_points", [])[:max_key_points],
            "topic": topic,
            "confidence": confidence,
            "companies": companies,
            "credit_impact": credit_impact,
            "relevance_keywords": relevance_keywords,
            "published_time": self._get_earliest_published_time(article),
        }

    def _parse_articles(self, json_output: Optional[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Parse articles from JSON output and group by static topic.

        Args:
            json_output: Full JSON digest output string.

        Returns:
            Dictionary mapping topic to list of article dicts, ordered by avg confidence.
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
                if topic not in TOPIC_PRIORITY:
                    logger.warning("unknown_topic_fallback", topic=topic)
                    topic = "other"

                if topic not in articles_by_topic:
                    articles_by_topic[topic] = []

                articles_by_topic[topic].append(self._parse_article_dict(article))

            # Sort articles within each topic by credit_impact priority, then confidence
            self._sort_articles_in_groups(articles_by_topic)

            # Order topics by average relevance score (highest first)
            return self._sort_groups_by_confidence(articles_by_topic)

        except json.JSONDecodeError as e:
            logger.warning("json_output_parse_failed", error=str(e))
            return {}

    def _regroup_by_llm_groups(
        self,
        json_output: Optional[str],
        article_groups: List[Dict[str, Any]],
    ) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """Regroup articles using LLM-generated thematic clusters.

        Args:
            json_output: Full JSON digest output string.
            article_groups: List of group dicts with label, icon, article_indices.

        Returns:
            OrderedDict mapping group label to article dicts, or None on failure.
        """
        if not json_output or not article_groups:
            return None

        try:
            data = json.loads(json_output)
            raw_articles = data.get("articles", [])
            if not raw_articles:
                return None

            # Parse all articles into display format (flat, indexed)
            parsed_articles = [self._parse_article_dict(a) for a in raw_articles]

            # Group by LLM clusters (preserve LLM order)
            grouped: Dict[str, List[Dict[str, Any]]] = {}
            for group in article_groups:
                label = group.get("label", "Weitere")
                indices = group.get("article_indices", [])

                group_articles = []
                for idx in indices:
                    if 1 <= idx <= len(parsed_articles):
                        group_articles.append(parsed_articles[idx - 1])

                if group_articles:
                    grouped[label] = group_articles

            if not grouped:
                return None

            # Sort articles within each group (same logic as static topics)
            self._sort_articles_in_groups(grouped)

            logger.info(
                "articles_regrouped_by_llm",
                group_count=len(grouped),
                article_count=sum(len(a) for a in grouped.values()),
            )

            return grouped

        except (json.JSONDecodeError, Exception) as e:
            logger.warning("llm_regrouping_failed", error=str(e))
            return None

    @staticmethod
    def _sort_articles_in_groups(
        groups: Dict[str, List[Dict[str, Any]]],
    ) -> None:
        """Sort articles within each group by credit_impact priority, then confidence."""
        credit_impact_priority = {"negative": 0, "neutral": 1, "positive": 2}
        for group_articles in groups.values():
            group_articles.sort(
                key=lambda a: (
                    credit_impact_priority.get(a.get("credit_impact", "neutral"), 2),
                    -a.get("confidence", 0),
                ),
            )

    @staticmethod
    def _sort_groups_by_confidence(
        groups: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Sort groups by average confidence score (highest first)."""

        def _avg_confidence(topic_articles: List[Dict[str, Any]]) -> float:
            scores = [a.get("confidence", 0) for a in topic_articles]
            return sum(scores) / len(scores) if scores else 0

        sorted_topics = sorted(
            [t for t in groups if groups[t]],
            key=lambda t: _avg_confidence(groups[t]),
            reverse=True,
        )
        return {t: groups[t] for t in sorted_topics}

    def _truncate_summary(self, summary: str, max_length: int = 300) -> str:
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

    def _determine_risk_level(self, topic: str, confidence: float) -> str:
        """Determine visual risk level for an article.

        Args:
            topic: Article topic classification.
            confidence: Confidence score of the classification.

        Returns:
            "elevated" for high-risk articles, "standard" otherwise.
        """
        # High-risk topic with high confidence = elevated risk
        if topic in HIGH_RISK_TOPICS and confidence >= HIGH_CONFIDENCE_THRESHOLD:
            return "elevated"
        return "standard"

    def _extract_relevance_keywords(
        self, entities: Dict[str, Any], topic: str
    ) -> List[str]:
        """Extract relevance keywords explaining why an article is relevant.

        Args:
            entities: Extracted entities from the article.
            topic: Article topic classification.

        Returns:
            List of relevance keywords (max 3).
        """
        keywords = []

        if not entities:
            return keywords

        # Add topic keywords (most relevant to why article was selected)
        entity_topics = entities.get("topics", [])
        if entity_topics:
            # Take first 2 topic keywords
            keywords.extend(entity_topics[:2])

        # Add company names if relevant
        companies = entities.get("companies", [])
        if companies and len(keywords) < 3:
            # Add first company if we have room
            keywords.append(companies[0])

        # Limit to 3 keywords
        return keywords[:3]

    @staticmethod
    def _count_credit_impacts(
        articles_by_topic: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, int]:
        """Count articles by credit impact level.

        Args:
            articles_by_topic: Dictionary mapping topic to article dicts.

        Returns:
            Dictionary with negative, neutral, positive counts.
        """
        counts = {"negative": 0, "neutral": 0, "positive": 0}
        for articles in articles_by_topic.values():
            for article in articles:
                impact = article.get("credit_impact", "neutral")
                if impact in counts:
                    counts[impact] += 1
                else:
                    counts["neutral"] += 1
        return counts

    @staticmethod
    def _get_software_version() -> str:
        """Get software version from pyproject.toml or importlib metadata."""
        try:
            from importlib.metadata import version

            return version("newsanalysis")
        except Exception:
            return "unknown"

    @staticmethod
    def _parse_published_dt(published_at: str | None) -> datetime | None:
        """Parse published_at string to datetime, or None if invalid/midnight."""
        if not published_at:
            return None
        try:
            dt = datetime.fromisoformat(published_at)
            # Midnight = date-only feed, no real publication time
            if dt.hour == 0 and dt.minute == 0:
                return None
            return dt
        except (ValueError, TypeError):
            return None

    def _get_earliest_published_time(self, article: dict) -> str:
        """Get earliest publication time from article and its duplicate sources.

        For grouped articles, shows the earliest time any source published
        the story (e.g. "Heute, 08:31" or "Gestern, 18:12").

        Args:
            article: Article dict with published_at and duplicate_sources.

        Returns:
            Formatted string like "Heute, 08:31" or "Gestern, 18:12" or "".
        """
        candidates = []

        # Main article
        dt = self._parse_published_dt(article.get("published_at"))
        if dt:
            candidates.append(dt)

        # Duplicate sources
        for dup in article.get("duplicate_sources", []):
            dup_dt = self._parse_published_dt(dup.get("published_at"))
            if dup_dt:
                candidates.append(dup_dt)

        if not candidates:
            return ""

        earliest = min(candidates)
        now = datetime.now(earliest.tzinfo) if earliest.tzinfo else datetime.now()
        today = now.date()

        time_str = earliest.strftime("%H:%M")
        if earliest.date() == today:
            return f"Heute, {time_str}"
        elif earliest.date() == today - timedelta(days=1):
            return f"Gestern, {time_str}"
        else:
            day = earliest.day
            month = self._german_month_name(earliest.month)
            return f"{day}. {month}, {time_str}"

    @staticmethod
    def _german_month_name(month: int) -> str:
        """Return German month name."""
        names = {
            1: "Jan.", 2: "Feb.", 3: "März", 4: "Apr.", 5: "Mai", 6: "Juni",
            7: "Juli", 8: "Aug.", 9: "Sep.", 10: "Okt.", 11: "Nov.", 12: "Dez.",
        }
        return names.get(month, str(month))

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

    def get_top_article_title(
        self, digest_data: Dict[str, Any], max_length: int = 50
    ) -> Optional[str]:
        """Extract the top article title for subject line.

        Args:
            digest_data: Dictionary from DigestRepository.get_digest_by_date().
            max_length: Maximum title length before truncation.

        Returns:
            Top article title, truncated if necessary, or None if no articles.
        """
        articles_by_topic = self._parse_articles(digest_data.get("json_output"))

        if not articles_by_topic:
            return None

        # Get first article from first topic (highest priority)
        for topic_articles in articles_by_topic.values():
            if topic_articles:
                title = topic_articles[0].get("title", "")

                if not title:
                    continue

                # Truncate at word boundary if too long
                if len(title) > max_length:
                    truncated = title[:max_length]
                    last_space = truncated.rfind(" ")
                    if last_space > max_length // 2:
                        return truncated[:last_space] + "..."
                    return truncated + "..."

                return title

        return None

    def format_with_images(
        self,
        digest_data: Dict[str, Any],
        include_images: bool = True,
        pipeline_stats: Optional[Dict[str, int]] = None,
        feed_stats: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, Dict[str, str]]:
        """Format digest data as HTML email with embedded images.

        Args:
            digest_data: Dictionary from DigestRepository.get_digest_by_date().
            include_images: Whether to include article images (default: True).
            pipeline_stats: Optional dict with collected, filtered, rejected, deduplicated counts.
            feed_stats: Optional list of dicts with source, total, matched, rejected per feed.

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

        # Try dynamic LLM grouping first, fall back to static topics
        use_dynamic_groups = False
        group_icons: Dict[str, str] = {}
        article_groups = meta_analysis.get("article_groups", [])

        articles_by_topic = self._regroup_by_llm_groups(
            digest_data.get("json_output"), article_groups
        )
        if articles_by_topic:
            use_dynamic_groups = True
            group_icons = {g.get("label", ""): g.get("icon", "") for g in article_groups}
        else:
            articles_by_topic = self._parse_articles(digest_data.get("json_output"))

        # Fetch article images if repository available and images enabled
        image_cid_mapping: Dict[str, str] = {}
        if include_images and self.article_repository:
            image_cid_mapping = self._prepare_article_images(articles_by_topic)

        # Use Swiss flag as placeholder for articles without images
        if SWISS_FLAG_PATH.exists():
            for topic, articles in articles_by_topic.items():
                for article in articles:
                    if "image_cid" not in article:
                        article["image_cid"] = SWISS_FLAG_CID

        # Add Swiss flag logo to image attachments
        swiss_flag_cid = None
        if SWISS_FLAG_PATH.exists():
            image_cid_mapping[SWISS_FLAG_CID] = str(SWISS_FLAG_PATH)
            swiss_flag_cid = SWISS_FLAG_CID
            logger.debug("swiss_flag_attached", path=str(SWISS_FLAG_PATH))
        else:
            logger.warning("swiss_flag_not_found", path=str(SWISS_FLAG_PATH))

        # Format date in German style
        digest_date = self._format_date(digest_data.get("digest_date"))

        # Count credit impact distribution
        credit_impact_counts = self._count_credit_impacts(articles_by_topic)

        # Get template and render
        template = self.env.get_template("email_digest.html")
        html = template.render(
            date=digest_date,
            article_count=digest_data.get("article_count", 0),
            executive_summary=meta_analysis.get("executive_summary", []),
            key_themes=meta_analysis.get("key_themes", []),
            credit_risk_signals=meta_analysis.get("credit_risk_signals", []),
            regulatory_updates=meta_analysis.get("regulatory_updates", []),
            market_insights=meta_analysis.get("market_insights", []),
            articles_by_topic=articles_by_topic,
            topic_translations=TOPIC_TRANSLATIONS,
            topic_icons=TOPIC_ICONS,
            credit_impact_counts=credit_impact_counts,
            version=self._get_software_version(),
            generated_at=digest_data.get("generated_at", ""),
            images_enabled=include_images,
            pipeline_stats=pipeline_stats or {},
            feed_stats=feed_stats or [],
            swiss_flag_cid=swiss_flag_cid,
            use_dynamic_groups=use_dynamic_groups,
            group_icons=group_icons,
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

