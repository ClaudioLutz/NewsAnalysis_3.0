"""German report formatter."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from newsanalysis.core.digest import DailyDigest
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)

# German month names (locale-independent)
GERMAN_MONTHS = {
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

# Topic display priority (risk-critical first)
TOPIC_PRIORITY = [
    "insolvency_bankruptcy",
    "credit_risk",
    "regulatory_compliance",
    "data_protection",
    "kyc_aml_sanctions",
    "payment_behavior",
    "debt_collection",
    "board_changes",
    "company_lifecycle",
    "economic_indicators",
    "market_intelligence",
    "ecommerce_fraud",
    "business_scams",
]

# Topic translations (English to German)
TOPIC_TRANSLATIONS = {
    "insolvency_bankruptcy": "Insolvenzen",
    "credit_risk": "Bonität",
    "regulatory_compliance": "Regulierung",
    "data_protection": "Datenschutz",
    "kyc_aml_sanctions": "Sanktionen & Compliance",
    "payment_behavior": "Zahlungsverhalten",
    "debt_collection": "Inkasso",
    "board_changes": "Mutationen Gremien",
    "company_lifecycle": "Fusionen & Übernahmen",
    "economic_indicators": "Wirtschaftsindikatoren",
    "market_intelligence": "Marktentwicklungen",
    "ecommerce_fraud": "Online-Betrug",
    "business_scams": "Wirtschaftsdelikte",
    # Legacy mappings for backwards compatibility
    "other": "Sonstige",
    "bankruptcies": "Insolvenzen",
    "financial_distress": "Finanzielle Schwierigkeiten",
    "creditreform_insights": "Creditreform Insights",
    "creditworthiness": "Bonität",
    "industry_trends": "Branchentrends",
    "regulatory": "Regulierung",
    "market_developments": "Marktentwicklungen",
    "legal": "Rechtliches",
    "mergers_acquisitions": "Fusionen & Übernahmen",
    "Other": "Sonstige",
    "Sonstige": "Sonstige",
}


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

        # Format dates with German month names (locale-independent)
        month_name = GERMAN_MONTHS[digest.date.month]
        date_str = f"{digest.date.day:02d}. {month_name} {digest.date.year}"
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
        return TOPIC_TRANSLATIONS.get(topic, topic)
