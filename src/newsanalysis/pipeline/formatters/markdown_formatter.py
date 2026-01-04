"""Markdown output formatter."""

from newsanalysis.core.digest import DailyDigest
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


class MarkdownFormatter:
    """Format digest as Markdown report."""

    def format(self, digest: DailyDigest) -> str:
        """Format digest as Markdown.

        Args:
            digest: Daily digest to format.

        Returns:
            Markdown string.
        """
        logger.info("formatting_markdown_digest", date=str(digest.date))

        try:
            lines = []

            # Header
            lines.append(f"# News Digest - {digest.date.strftime('%B %d, %Y')}")
            lines.append("")
            lines.append(f"**Version**: {digest.version}  ")
            lines.append(f"**Articles**: {digest.article_count}  ")
            lines.append(f"**Generated**: {digest.generated_at.strftime('%Y-%m-%d %H:%M:%S')}  ")
            lines.append("")

            # Meta-Analysis Section
            lines.append("## Executive Summary")
            lines.append("")

            if digest.meta_analysis.key_themes:
                lines.append("### Key Themes")
                for theme in digest.meta_analysis.key_themes:
                    lines.append(f"- {theme}")
                lines.append("")

            if digest.meta_analysis.credit_risk_signals:
                lines.append("### Credit Risk Signals")
                for signal in digest.meta_analysis.credit_risk_signals:
                    lines.append(f"- {signal}")
                lines.append("")

            if digest.meta_analysis.regulatory_updates:
                lines.append("### Regulatory Updates")
                for update in digest.meta_analysis.regulatory_updates:
                    lines.append(f"- {update}")
                lines.append("")

            if digest.meta_analysis.market_insights:
                lines.append("### Market Insights")
                for insight in digest.meta_analysis.market_insights:
                    lines.append(f"- {insight}")
                lines.append("")

            # Articles Section
            lines.append("---")
            lines.append("")
            lines.append("## Articles")
            lines.append("")

            # Group articles by topic
            by_topic = self._group_by_topic(digest.articles)

            for topic, articles in by_topic.items():
                lines.append(f"### {topic}")
                lines.append("")

                for article in articles:
                    lines.extend(self._format_article(article))
                    lines.append("")

            markdown_output = "\n".join(lines)

            logger.info("markdown_formatted", size=len(markdown_output))

            return markdown_output

        except Exception as e:
            logger.error("markdown_formatting_failed", error=str(e))
            raise

    def _group_by_topic(self, articles):
        """Group articles by topic.

        Args:
            articles: List of articles.

        Returns:
            Dictionary of topic -> articles.
        """
        by_topic = {}

        for article in articles:
            topic = article.topic or "Other"

            if topic not in by_topic:
                by_topic[topic] = []

            by_topic[topic].append(article)

        return by_topic

    def _format_article(self, article):
        """Format single article as Markdown.

        Args:
            article: Article object.

        Returns:
            List of Markdown lines.
        """
        lines = []

        # Title with link
        title = article.summary_title or article.title
        lines.append(f"#### [{title}]({article.url})")
        lines.append("")

        # Metadata line
        metadata = []
        if article.source:
            metadata.append(f"**Source**: {article.source}")
        if article.confidence:
            metadata.append(f"**Confidence**: {article.confidence:.0%}")
        if article.published_at:
            metadata.append(f"**Published**: {article.published_at.strftime('%Y-%m-%d')}")

        if metadata:
            lines.append(" | ".join(metadata))
            lines.append("")

        # Summary
        if article.summary:
            lines.append(article.summary)
            lines.append("")

        # Key points
        if article.key_points:
            lines.append("**Key Points:**")
            for point in article.key_points:
                lines.append(f"- {point}")
            lines.append("")

        # Entities
        if article.entities:
            entity_parts = []

            if isinstance(article.entities, dict):
                companies = article.entities.get("companies", [])
                people = article.entities.get("people", [])
                locations = article.entities.get("locations", [])
            else:
                # EntityData object
                companies = article.entities.companies
                people = article.entities.people
                locations = article.entities.locations

            if companies:
                entity_parts.append(f"**Companies**: {', '.join(companies)}")
            if people:
                entity_parts.append(f"**People**: {', '.join(people)}")
            if locations:
                entity_parts.append(f"**Locations**: {', '.join(locations)}")

            if entity_parts:
                lines.append(" | ".join(entity_parts))
                lines.append("")

        lines.append("---")

        return lines
