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

# Required filter for valid Pool_Adresse records
_POOL_ADRESSE_FILTER = (
    "Pa_S_Adrart = 'F' "
    "AND Pa_S_Adrtyp = 1 "
    "AND Pa_S_SperrCode != 'XX' "
    "AND Pa_S_Land = 'CH'"
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
    """Normalize a company name for comparison."""
    name = name.lower().strip()
    name = _LEGAL_SUFFIXES.sub("", name)
    name = _PUNCT.sub(" ", name)
    name = _WHITESPACE.sub(" ", name).strip()
    return name


class CompanyMatcher:
    """Matches article company names against Pool_Adresse in CnZenReport DB.

    Uses batch queries to resolve all names efficiently:
    1. Single batch exact-match query for all names at once
    2. Individual LIKE fallback only for unmatched names (min 3 chars)

    All queries filter for valid Swiss firm addresses only
    (Adrart=F, Adrtyp=1, SperrCode!=XX, Land=CH).

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
            logger.info(
                "cnc_db_connected",
                server=self._conn_str.split("SERVER=")[1].split(";")[0],
            )
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
    # Batch matching (primary approach)
    # ------------------------------------------------------------------

    def _batch_exact_match(self, names: list[str]) -> dict[str, tuple[int, str]]:
        """Batch exact match — one query for all names.

        Returns dict mapping lowercase-trimmed name → (Pa_L_Nr, Pa_S_Firma).
        """
        assert self._conn is not None
        if not names:
            return {}

        placeholders = ",".join("?" for _ in names)
        params = [n.strip().lower() for n in names]

        try:
            cursor = self._conn.cursor()
            cursor.execute(
                f"SELECT Pa_L_Nr, Pa_S_Firma "
                f"FROM Pool_Adresse "
                f"WHERE {_POOL_ADRESSE_FILTER} "
                f"AND LTRIM(RTRIM(LOWER(Pa_S_Firma))) IN ({placeholders})",
                params,
            )
            results: dict[str, tuple[int, str]] = {}
            for row in cursor.fetchall():
                db_name = str(row[1]).strip().lower()
                if db_name not in results:
                    results[db_name] = (int(row[0]), str(row[1]))
            logger.info(
                "company_batch_exact",
                queried=len(names),
                matched=len(results),
            )
            return results
        except pyodbc.Error as exc:
            logger.warning("company_batch_exact_failed", error=str(exc))
            return {}

    def _query_like(self, name: str) -> tuple[int, str] | None:
        """LIKE fallback for a single unmatched name — pick shortest match."""
        assert self._conn is not None
        normalized = _normalize(name)
        if len(normalized) < 3:
            return None

        try:
            cursor = self._conn.cursor()
            cursor.execute(
                f"SELECT TOP 5 Pa_L_Nr, Pa_S_Firma "
                f"FROM Pool_Adresse "
                f"WHERE {_POOL_ADRESSE_FILTER} "
                f"AND LOWER(Pa_S_Firma) LIKE ? "
                f"ORDER BY LEN(Pa_S_Firma) ASC",
                (f"%{normalized}%",),
            )
            rows = cursor.fetchall()
            if rows:
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
    # Public API
    # ------------------------------------------------------------------

    def resolve_companies(self, companies: list[str]) -> list[dict[str, str]]:
        """Resolve a list of company names to display dicts.

        Efficiently batches exact matches, then falls back to LIKE for unmatched.

        Returns list of dicts with keys:
            - name: original company name
            - url: crediweb URL if matched, else empty string
        """
        if not self.is_connected or not companies:
            return [{"name": c, "url": ""} for c in companies]

        # Deduplicate and filter cached
        uncached = []
        for c in companies:
            key = _normalize(c)
            if key and key not in self._cache:
                uncached.append(c)

        # Stage 1: Batch exact match for all uncached names in one query
        if uncached:
            exact_results = self._batch_exact_match(uncached)

            # Populate cache from batch results
            matched_keys: set[str] = set()
            for c in uncached:
                key = _normalize(c)
                lookup = c.strip().lower()
                if lookup in exact_results:
                    self._cache[key] = exact_results[lookup]
                    matched_keys.add(key)

            # Stage 2: LIKE fallback only for unmatched (typically few)
            for c in uncached:
                key = _normalize(c)
                if key not in matched_keys and key not in self._cache:
                    self._cache[key] = self._query_like(c)

        # Build results
        results: list[dict[str, str]] = []
        for company in companies:
            key = _normalize(company)
            match = self._cache.get(key) if key else None
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
