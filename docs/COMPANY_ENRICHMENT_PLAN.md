# Company Solvability Score Enrichment

## Overview

This document outlines the architecture for enriching news digest articles with company solvability scores from the Creditreform database.

**Challenge**: Match company names extracted from news articles (often abbreviated or without legal suffixes) against a database of ~1 million companies, then retrieve their solvability scores from a 50+ million row score table.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  DIGEST ENRICHMENT PIPELINE                                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 1: PREPROCESS (Python)                                             │
│  ───────────────────────────────────────────────────────────────────────│
│  • Normalize: lowercase, strip "AG/GmbH/SA/Sàrl"                         │
│  • Generate block keys: first-4-chars, first-3-chars                     │
│  • SOUNDEX computed by SQL Server (not Python!)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 2: CACHE CHECK (Redis or in-memory)                                │
│  ───────────────────────────────────────────────────────────────────────│
│  • LRU cache of recent lookups (hit rate 60-80%)                         │
│  • Cache "not found" results too (prevent repeated misses)               │
│  • TTL: 24-48 hours                                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │ cache miss
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 3: SQL SERVER CANDIDATE QUERY                                      │
│  ───────────────────────────────────────────────────────────────────────│
│  • Simple SELECT with WHERE clause on indexed columns                    │
│  • SOUNDEX() comparison done natively by SQL Server                      │
│  • Returns ~20 candidates for Python to score                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 4: FUZZY SCORING (Python + RapidFuzz)                              │
│  ───────────────────────────────────────────────────────────────────────│
│  • Score candidates with Jaro-Winkler / WRatio                           │
│  • Return best match above threshold                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 5: SCORE LOOKUP (Simple SQL query)                                 │
│  ───────────────────────────────────────────────────────────────────────│
│  • Only executed if company matched                                      │
│  • Index on CompanyID                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

## SQL Server Setup (One-time)

### Create Lookup Table with Computed Columns

SQL Server computes SOUNDEX automatically using computed columns:

```sql
-- Create lookup table with SQL-computed SOUNDEX (run once)
CREATE TABLE dbo.CompanyLookup (
    CompanyID INT NOT NULL,
    OriginalName NVARCHAR(500) NOT NULL,
    NormalizedName NVARCHAR(200) NOT NULL,

    -- Computed columns: SQL Server calculates and persists these automatically
    Block4 AS LEFT(NormalizedName, 4) PERSISTED,
    Block3 AS LEFT(NormalizedName, 3) PERSISTED,
    SoundexCode AS SOUNDEX(NormalizedName) PERSISTED,  -- SQL Server computes SOUNDEX!

    CONSTRAINT PK_CompanyLookup PRIMARY KEY (CompanyID)
);

-- Create indexes for fast lookups
CREATE INDEX IX_CompanyLookup_Exact ON dbo.CompanyLookup (NormalizedName);
CREATE INDEX IX_CompanyLookup_Block4 ON dbo.CompanyLookup (Block4) INCLUDE (NormalizedName, CompanyID, OriginalName);
CREATE INDEX IX_CompanyLookup_Block3 ON dbo.CompanyLookup (Block3) INCLUDE (NormalizedName, CompanyID, OriginalName);
CREATE INDEX IX_CompanyLookup_Soundex ON dbo.CompanyLookup (SoundexCode) INCLUDE (NormalizedName, CompanyID, OriginalName);
```

**Key advantage**: The `PERSISTED` keyword means SQL Server stores the computed values physically, so they're indexed and don't need to be recalculated on every query.

### Populate with Python Script

Much simpler now - just insert the normalized name, SQL handles the rest:

```python
"""One-time script to populate CompanyLookup table."""

import pyodbc
from typing import Iterator, Tuple

# Swiss/German legal suffixes to strip
LEGAL_SUFFIXES = [
    " ag", " gmbh", " sa", " sàrl", " sarl", " kg",
    " ohg", " & co", " und co", " inc", " ltd", " llc",
    " & cie", " et cie", " corp", " corporation",
]

def normalize_company_name(name: str) -> str:
    """Normalize company name for matching."""
    result = name.lower().strip()

    for suffix in LEGAL_SUFFIXES:
        if result.endswith(suffix):
            result = result[:-len(suffix)]
        result = result.replace(suffix + " ", " ")

    # Remove punctuation
    for char in ".,;:!?()[]{}\"'":
        result = result.replace(char, "")

    # Collapse whitespace
    return " ".join(result.split())


def generate_lookup_rows(conn_str: str) -> Iterator[Tuple]:
    """Generate lookup rows from Companies table."""
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT CompanyID, Name FROM dbo.Companies")

        for row in cursor:
            company_id, name = row
            normalized = normalize_company_name(name)

            # Only need to provide CompanyID, OriginalName, NormalizedName
            # SQL Server computes Block4, Block3, SoundexCode automatically!
            yield (company_id, name, normalized)


def populate_lookup_table(conn_str: str, batch_size: int = 10000):
    """Populate the lookup table in batches."""
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()

        # Clear existing data
        cursor.execute("TRUNCATE TABLE dbo.CompanyLookup")

        batch = []
        total = 0

        for row in generate_lookup_rows(conn_str):
            batch.append(row)

            if len(batch) >= batch_size:
                cursor.executemany(
                    """
                    INSERT INTO dbo.CompanyLookup
                    (CompanyID, OriginalName, NormalizedName)
                    VALUES (?, ?, ?)
                    """,
                    batch,
                )
                conn.commit()
                total += len(batch)
                print(f"Inserted {total} rows...")
                batch = []

        # Insert remaining
        if batch:
            cursor.executemany(
                """
                INSERT INTO dbo.CompanyLookup
                (CompanyID, OriginalName, NormalizedName)
                VALUES (?, ?, ?)
                """,
                batch,
            )
            conn.commit()
            total += len(batch)

        print(f"Done! Total: {total} rows")


if __name__ == "__main__":
    CONN_STR = "Driver={ODBC Driver 17 for SQL Server};Server=...;Database=...;Trusted_Connection=yes;"
    populate_lookup_table(CONN_STR)
```

## Python Implementation

### Dependencies

```
rapidfuzz>=3.0.0
pyodbc>=4.0.0
```

Optional (for caching):
```
redis>=4.0.0
```

### Company Matcher Service

No Python SOUNDEX needed - SQL Server handles it:

```python
"""Company name matching service with fuzzy search - using SQL Server SOUNDEX."""

from typing import Any, Dict, List, Optional

import pyodbc
from rapidfuzz import fuzz


class CompanyMatcher:
    """Matches company names against Creditreform database."""

    # Swiss/German legal suffixes to strip during normalization
    LEGAL_SUFFIXES = [
        " ag", " gmbh", " sa", " sàrl", " sarl", " kg",
        " ohg", " & co", " und co", " inc", " ltd", " llc",
        " & cie", " et cie", " corp", " corporation",
    ]

    def __init__(
        self,
        sql_connection_string: str,
        match_threshold: int = 85,
        max_candidates: int = 20,
    ):
        """Initialize matcher.

        Args:
            sql_connection_string: ODBC connection string for SQL Server.
            match_threshold: Minimum fuzzy score to accept (0-100).
            max_candidates: Maximum candidates to retrieve from SQL.
        """
        self.sql_conn_str = sql_connection_string
        self.match_threshold = match_threshold
        self.max_candidates = max_candidates

        # In-memory cache (use Redis for production)
        self._cache: Dict[str, Optional[Dict]] = {}
        self._score_cache: Dict[int, Optional[int]] = {}

    def normalize(self, name: str) -> str:
        """Normalize company name for matching."""
        result = name.lower().strip()

        for suffix in self.LEGAL_SUFFIXES:
            if result.endswith(suffix):
                result = result[:-len(suffix)]
            result = result.replace(suffix + " ", " ")

        # Remove punctuation
        for char in ".,;:!?()[]{}\"'":
            result = result.replace(char, "")

        return " ".join(result.split())

    def match(self, company_name: str) -> Optional[Dict[str, Any]]:
        """Match company name and return match info.

        Args:
            company_name: Company name from news article.

        Returns:
            Dict with company_id, matched_name, score, match_type
            or None if no match found.
        """
        normalized = self.normalize(company_name)

        # Check cache
        if normalized in self._cache:
            return self._cache[normalized]

        # Generate blocking keys (SOUNDEX computed by SQL!)
        block4 = normalized[:4].ljust(4) if len(normalized) >= 4 else normalized.ljust(4)
        block3 = normalized[:3].ljust(3) if len(normalized) >= 3 else normalized.ljust(3)

        # Get candidates - SQL Server does the SOUNDEX comparison
        candidates = self._get_candidates(normalized, block4, block3)

        if not candidates:
            self._cache[normalized] = None
            return None

        # Check for exact match first
        for c in candidates:
            if c["NormalizedName"] == normalized:
                result = {
                    "company_id": c["CompanyID"],
                    "matched_name": c["OriginalName"],
                    "score": 100,
                    "match_type": "EXACT",
                }
                self._cache[normalized] = result
                return result

        # Score candidates with RapidFuzz
        best_match = None
        best_score = 0

        for c in candidates:
            score = fuzz.WRatio(normalized, c["NormalizedName"])

            if score > best_score:
                best_score = score
                best_match = c

        # Apply threshold
        if best_match and best_score >= self.match_threshold:
            result = {
                "company_id": best_match["CompanyID"],
                "matched_name": best_match["OriginalName"],
                "score": best_score,
                "match_type": "FUZZY",
            }
            self._cache[normalized] = result
            return result

        self._cache[normalized] = None
        return None

    def _get_candidates(
        self,
        normalized: str,
        block4: str,
        block3: str,
    ) -> List[Dict[str, Any]]:
        """Get candidate matches from SQL Server.

        SQL Server computes SOUNDEX at query time for the input,
        and compares against pre-computed SOUNDEX in the table.
        """

        # SQL Server SOUNDEX() is used directly in the WHERE clause
        query = """
            SELECT DISTINCT TOP (?)
                CompanyID,
                OriginalName,
                NormalizedName
            FROM dbo.CompanyLookup
            WHERE NormalizedName = ?              -- Exact match
               OR Block4 = ?                      -- First 4 chars
               OR Block3 = ?                      -- First 3 chars
               OR SoundexCode = SOUNDEX(?)        -- SQL Server computes SOUNDEX!
            ORDER BY
                CASE WHEN NormalizedName = ? THEN 0 ELSE 1 END
        """

        with pyodbc.connect(self.sql_conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                self.max_candidates,
                normalized,
                block4,
                block3,
                normalized,  # SQL Server computes SOUNDEX(normalized)
                normalized,
            )

            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_solvability_score(self, company_id: int) -> Optional[int]:
        """Get latest solvability score for a company."""

        # Check cache
        if company_id in self._score_cache:
            return self._score_cache[company_id]

        query = """
            SELECT TOP 1 Score
            FROM dbo.CompanyScores
            WHERE CompanyID = ?
            ORDER BY ScoreDate DESC
        """

        with pyodbc.connect(self.sql_conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute(query, company_id)
            row = cursor.fetchone()
            score = row[0] if row else None

        self._score_cache[company_id] = score
        return score

    def match_with_score(self, company_name: str) -> Optional[Dict[str, Any]]:
        """Match company and get score in one call."""
        match = self.match(company_name)

        if match:
            score = self.get_solvability_score(match["company_id"])
            return {**match, "solvability_score": score}

        return None

    def clear_cache(self):
        """Clear in-memory caches."""
        self._cache.clear()
        self._score_cache.clear()
```

### Usage Example

```python
# Initialize
matcher = CompanyMatcher(
    sql_connection_string="Driver={ODBC Driver 17 for SQL Server};Server=myserver;Database=mydb;Trusted_Connection=yes;",
    match_threshold=85,
)

# Single lookup
result = matcher.match_with_score("Wonderwaffel Spreitenbach")
if result:
    print(f"Matched: {result['matched_name']}")
    print(f"Score: {result['solvability_score']}")
    print(f"Confidence: {result['score']}%")

# Batch lookup for digest
companies = ["Credit Suisse", "UBS AG", "Novartis", "Unknown Company XYZ"]

for company in companies:
    result = matcher.match_with_score(company)
    if result:
        print(f"{company} → {result['matched_name']} (solvability: {result['solvability_score']})")
    else:
        print(f"{company} → No match found")
```

### Digest Enrichment Integration

```python
"""Enrich digest articles with company solvability scores."""

from typing import Any, Dict, List


def enrich_digest_companies(
    articles: List[Dict[str, Any]],
    matcher: "CompanyMatcher",
) -> List[Dict[str, Any]]:
    """Batch enrich all companies in digest articles.

    Args:
        articles: List of article dicts with 'companies' field.
        matcher: Initialized CompanyMatcher instance.

    Returns:
        Articles with added 'company_scores' field.
    """
    # Collect unique company names
    all_companies = set()
    for article in articles:
        all_companies.update(article.get("companies", []))

    # Match all companies
    matches = {}
    for company in all_companies:
        result = matcher.match_with_score(company)
        if result:
            matches[company] = result

    # Enrich articles
    for article in articles:
        article["company_scores"] = {
            company: matches[company]
            for company in article.get("companies", [])
            if company in matches
        }

    return articles
```

## Performance

| Step | Time | Notes |
|------|------|-------|
| Cache hit | <1ms | In-memory dict lookup |
| SQL candidate query | 5-20ms | With indexes, SOUNDEX is fast |
| RapidFuzz scoring | <1ms | ~20 candidates |
| Score lookup | 2-5ms | Indexed |
| **Total (cache miss)** | **~25ms** | Per company |
| **Total (cache hit)** | **<1ms** | Per company |

## SQL Queries Used

Only two simple queries - no procedures or functions:

### 1. Get Candidates (SQL Server SOUNDEX)

```sql
SELECT DISTINCT TOP (20)
    CompanyID,
    OriginalName,
    NormalizedName
FROM dbo.CompanyLookup
WHERE NormalizedName = @normalized
   OR Block4 = @block4
   OR Block3 = @block3
   OR SoundexCode = SOUNDEX(@normalized)  -- SQL computes this!
ORDER BY
    CASE WHEN NormalizedName = @normalized THEN 0 ELSE 1 END
```

### 2. Get Score

```sql
SELECT TOP 1 Score
FROM dbo.CompanyScores
WHERE CompanyID = @company_id
ORDER BY ScoreDate DESC
```

## How SQL Server SOUNDEX Works

SOUNDEX is a phonetic algorithm that encodes words by how they sound:

```sql
-- Examples
SELECT SOUNDEX('Meyer')   -- Returns 'M600'
SELECT SOUNDEX('Meier')   -- Returns 'M600'  (same!)
SELECT SOUNDEX('Maier')   -- Returns 'M600'  (same!)
SELECT SOUNDEX('Smith')   -- Returns 'S530'
SELECT SOUNDEX('Smythe')  -- Returns 'S530'  (same!)
```

**Algorithm**:
1. Keep the first letter
2. Replace consonants with digits (B,F,P,V→1, C,G,J,K,Q,S,X,Z→2, D,T→3, L→4, M,N→5, R→6)
3. Remove vowels and H,W,Y
4. Remove consecutive duplicates
5. Pad/truncate to 4 characters

SQL Server also has `DIFFERENCE()` which returns 0-4 based on SOUNDEX similarity:
```sql
SELECT DIFFERENCE('Meyer', 'Meier')  -- Returns 4 (identical SOUNDEX)
SELECT DIFFERENCE('Meyer', 'Smith')  -- Returns 1 (very different)
```

## Blocking Strategy

**Why blocking?** Without it, comparing every company name against 1M records requires 1M comparisons per lookup.

| Blocking Key | What it catches | Computed by |
|--------------|-----------------|-------------|
| `Block4` | Same first 4 chars: "wonderwaffel" ↔ "wonderwafel" | SQL (persisted) |
| `Block3` | Same first 3 chars: "credit" ↔ "creditreform" | SQL (persisted) |
| `SoundexCode` | Sounds similar: "Meyer" ↔ "Meier" ↔ "Maier" | SQL (persisted) |

All blocking keys are computed by SQL Server as `PERSISTED` computed columns - no Python SOUNDEX implementation needed!

## Key Simplification

By using SQL Server's native SOUNDEX:

1. **No Python SOUNDEX function** - one less thing to maintain
2. **Guaranteed consistency** - SQL computes SOUNDEX the same way for both stored values and query input
3. **Computed columns** - SQL Server handles the computation automatically on INSERT
4. **Indexed** - The `PERSISTED` keyword means values are stored and can be indexed

## References

- [SQL Server SOUNDEX](https://docs.microsoft.com/en-us/sql/t-sql/functions/soundex-transact-sql)
- [SQL Server DIFFERENCE](https://docs.microsoft.com/en-us/sql/t-sql/functions/difference-transact-sql)
- [RapidFuzz Documentation](https://rapidfuzz.github.io/RapidFuzz/)
- [pyodbc Documentation](https://github.com/mkleehammer/pyodbc/wiki)
