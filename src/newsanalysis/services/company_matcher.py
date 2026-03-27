"""Company matching service — matches extracted company names against Creditreform DB."""

import re

import pyodbc

from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)

# URL template for crediweb company search
CREDIWEB_URL_TEMPLATE = (
    "https://www.crediweb.ch/Search/GetSearchResult"
    "?what={crefo_id}&comparisonMode=Regular&searchFromFilter=False"
    "&hitsPerPage=20&isMonitored=False"
)

# Legal suffixes to strip during normalization
_LEGAL_SUFFIXES = re.compile(
    r"\b("
    r"ag|gmbh|sa|s\.a\.|sarl|s\.à\.r\.l\.|ltd|limited|inc|plc|se|co\.|"
    r"genossenschaft|stiftung|verein|holding|group|corp|corporation"
    r")\b",
    re.IGNORECASE,
)

# Extra whitespace / punctuation cleanup
_WHITESPACE = re.compile(r"\s+")
_PUNCT = re.compile(r"[.,;:()\-/&\"]")


def _normalize(name: str) -> str:
    """Normalize a company name for comparison.

    Lowercases, strips legal suffixes (AG, GmbH, SA, …), removes punctuation,
    collapses whitespace.
    """
    name = name.lower().strip()
    name = _LEGAL_SUFFIXES.sub("", name)
    name = _PUNCT.sub(" ", name)
    name = _WHITESPACE.sub(" ", name).strip()
    return name


class CompanyMatcher:
    """Matches article company names against Pool_Adresse in CNC Report DB.

    Uses a two-stage strategy:
    1. Exact match on normalized name
    2. LIKE fallback (shortest match wins)

    Results are cached in-memory per session so identical names are queried only once.
    """

    def __init__(
        self,
        db_server: str,
        db_database: str,
        db_driver: str = "ODBC Driver 17 for SQL Server",
    ) -> None:
        self._conn_str = (
            f"DRIVER={{{db_driver}}};"
            f"SERVER={db_server};"
            f"DATABASE={db_database};"
            f"Trusted_Connection=yes;"
        )
        self._cache: dict[str, tuple[int, str] | None] = {}
        self._conn: pyodbc.Connection | None = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open MSSQL connection (Windows auth)."""
        if self._conn is not None:
            return
        try:
            self._conn = pyodbc.connect(self._conn_str, timeout=10)
            logger.info("cnc_db_connected", server=self._conn_str.split("SERVER=")[1].split(";")[0])
        except pyodbc.Error as exc:
            logger.error("cnc_db_connection_failed", error=str(exc))
            self._conn = None

    def close(self) -> None:
        """Close the DB connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    # ------------------------------------------------------------------
    # Core matching
    # ------------------------------------------------------------------

    def match_company(self, name: str) -> tuple[int, str] | None:
        """Match a single company name against Pool_Adresse.

        Returns:
            (Pa_L_Nr, Pa_S_Firma) tuple if found, else None.
        """
        if not self.is_connected:
            return None

        # Check cache first
        cache_key = _normalize(name)
        if not cache_key:
            return None
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = self._query_exact(name) or self._query_like(name)
        self._cache[cache_key] = result
        return result

    def _query_exact(self, name: str) -> tuple[int, str] | None:
        """Stage 1: Exact match (case-insensitive, trimmed)."""
        assert self._conn is not None
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT TOP 1 Pa_L_Nr, Pa_S_Firma "
                "FROM Pool_Adresse "
                "WHERE LTRIM(RTRIM(LOWER(Pa_S_Firma))) = LTRIM(RTRIM(LOWER(?)))",
                (name.strip(),),
            )
            row = cursor.fetchone()
            if row:
                logger.debug("company_match_exact", name=name, crefo_id=row[0])
                return (int(row[0]), str(row[1]))
        except pyodbc.Error as exc:
            logger.warning("company_match_query_failed", name=name, error=str(exc))
        return None

    def _query_like(self, name: str) -> tuple[int, str] | None:
        """Stage 2: LIKE fallback — pick shortest matching Pa_S_Firma."""
        assert self._conn is not None
        normalized = _normalize(name)
        if len(normalized) < 3:
            return None  # Too short for LIKE, would match too many

        try:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT TOP 10 Pa_L_Nr, Pa_S_Firma "
                "FROM Pool_Adresse "
                "WHERE Pa_S_Firma LIKE ? "
                "ORDER BY LEN(Pa_S_Firma) ASC",
                (f"%{normalized}%",),
            )
            rows = cursor.fetchall()
            if rows:
                # Pick the shortest name (most specific match)
                best = rows[0]
                logger.debug(
                    "company_match_like",
                    name=name,
                    crefo_id=best[0],
                    matched_name=best[1],
                    candidates=len(rows),
                )
                return (int(best[0]), str(best[1]))
        except pyodbc.Error as exc:
            logger.warning("company_match_like_failed", name=name, error=str(exc))
        return None

    # ------------------------------------------------------------------
    # Batch matching for digest
    # ------------------------------------------------------------------

    def resolve_companies(self, companies: list[str]) -> list[dict[str, str]]:
        """Resolve a list of company names to display dicts.

        Returns list of dicts with keys:
            - name: original company name
            - url: crediweb URL if matched, else empty string
        """
        results: list[dict[str, str]] = []
        for company in companies:
            match = self.match_company(company)
            if match:
                crefo_id, _db_name = match
                url = CREDIWEB_URL_TEMPLATE.format(crefo_id=crefo_id)
                results.append({"name": company, "url": url})
            else:
                results.append({"name": company, "url": ""})
        return results

    @staticmethod
    def build_crediweb_url(crefo_id: int) -> str:
        """Build crediweb search URL for a given CrefoID."""
        return CREDIWEB_URL_TEMPLATE.format(crefo_id=crefo_id)
