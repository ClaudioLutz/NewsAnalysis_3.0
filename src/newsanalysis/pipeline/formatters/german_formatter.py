"""German report formatter."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from newsanalysis.core.digest import DailyDigest
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


class GermanReportFormatter:
    """Format digest as German rating report (Bonitäts-Tagesanalyse)."""

    def __init__(self, template_dir: Path = None):
        """Initialize formatter.

        Args:
            template_dir: Directory containing Jinja2 templates.
                         Defaults to config/templates/.
        """
        if template_dir is None:
            # Default to config/templates/ in project root
            # Path: src/newsanalysis/pipeline/formatters/german_formatter.py -> 5 parents to project root
            template_dir = Path(__file__).parent.parent.parent.parent.parent / "config" / "templates"

        self.template_dir = template_dir

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        logger.info("german_formatter_initialized", template_dir=str(template_dir))

    def format(self, digest: DailyDigest) -> str:
        """Format digest as German report.

        Args:
            digest: Daily digest to format.

        Returns:
            German report string (Markdown format).
        """
        logger.info("formatting_german_digest", date=str(digest.date))

        try:
            # Load template
            template = self.env.get_template("german_report.md.j2")

            # Prepare context
            context = self._build_context(digest)

            # Render template
            report = template.render(**context)

            logger.info("german_formatted", size=len(report))

            return report

        except Exception as e:
            logger.error("german_formatting_failed", error=str(e))
            raise

    def _build_context(self, digest: DailyDigest) -> dict:
        """Build template context.

        Args:
            digest: Daily digest.

        Returns:
            Context dictionary for template.
        """
        # Group articles by topic
        articles_by_topic = {}
        for article in digest.articles:
            topic = self._translate_topic(article.topic or "Sonstige")

            if topic not in articles_by_topic:
                articles_by_topic[topic] = []

            articles_by_topic[topic].append(article)

        # Format dates
        date_str = digest.date.strftime("%d. %B %Y")
        generated_at_str = digest.generated_at.strftime("%d.%m.%Y %H:%M:%S")

        return {
            "date_str": date_str,
            "version": digest.version,
            "article_count": digest.article_count,
            "generated_at_str": generated_at_str,
            "meta_analysis": digest.meta_analysis,
            "articles_by_topic": articles_by_topic,
        }

    def _translate_topic(self, topic: str) -> str:
        """Translate topic to German.

        Args:
            topic: Topic in English.

        Returns:
            Topic in German.
        """
        translations = {
            "bankruptcies": "Insolvenzen",
            "financial_distress": "Finanzielle Schwierigkeiten",
            "debt_collection": "Inkasso & Forderungsmanagement",
            "creditreform_insights": "Creditreform Insights",
            "creditworthiness": "Bonität",
            "payment_behavior": "Zahlungsverhalten",
            "industry_trends": "Branchentrends",
            "regulatory": "Regulierung",
            "market_developments": "Marktentwicklungen",
            "legal": "Rechtliches",
            "mergers_acquisitions": "Fusionen & Übernahmen",
            "economic_indicators": "Wirtschaftsindikatoren",
            "Other": "Sonstige",
            "Sonstige": "Sonstige",
        }

        return translations.get(topic, topic)
