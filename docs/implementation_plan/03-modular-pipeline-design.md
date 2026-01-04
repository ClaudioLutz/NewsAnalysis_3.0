# Modular Pipeline Design

## Overview

The NewsAnalysis pipeline is built as five independent, composable modules with clear interfaces and responsibilities. This document defines the module architecture, data contracts, and integration patterns that enable testable, maintainable, and scalable news processing.

**Key Principle**: Each module is a black box with well-defined inputs, outputs, and error handling. Modules can be developed, tested, and optimized independently.

## Pipeline Flow

```
┌──────────────┐
│   Input      │
│  (Config)    │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│  Module 1: NewsCollector                    │
│  Input: Feed configs (YAML)                 │
│  Output: List[ArticleMetadata]              │
│  Purpose: Collect URLs from news sources    │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│  Module 2: ContentFilter                    │
│  Input: List[ArticleMetadata]               │
│  Output: List[FilteredArticle]              │
│  Purpose: AI classification (title/URL)     │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│  Module 3: ContentScraper                   │
│  Input: List[FilteredArticle]               │
│  Output: List[ScrapedArticle]               │
│  Purpose: Extract full article content      │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│  Module 4: ArticleSummarizer                │
│  Input: List[ScrapedArticle]                │
│  Output: List[SummarizedArticle]            │
│  Purpose: Generate AI summaries             │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│  Module 5: DigestGenerator                  │
│  Input: List[SummarizedArticle] + State     │
│  Output: DailyDigest                        │
│  Purpose: Meta-analysis & report generation │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│   Output     │
│ (JSON/MD)    │
└──────────────┘
```

## Module 1: NewsCollector

### Purpose
Collect article URLs and basic metadata from multiple Swiss news sources (RSS feeds, sitemaps, HTML pages).

### Interface

**Input**:
```python
@dataclass
class FeedConfig:
    name: str  # "NZZ", "Tages-Anzeiger", etc.
    type: Literal["rss", "sitemap", "html"]
    url: str
    priority: int  # 1=government, 2=financial, 3=general
    max_age_hours: int  # How far back to collect
    rate_limit_seconds: float  # Delay between requests
    selectors: Optional[Dict[str, str]]  # CSS selectors for HTML type
```

**Output**:
```python
@dataclass
class ArticleMetadata:
    url: str
    normalized_url: str  # URL with tracking params removed
    url_hash: str  # SHA-256 hash for deduplication
    title: str
    source: str  # Feed name
    published_at: Optional[datetime]
    collected_at: datetime
    feed_priority: int
```

### Responsibilities
1. **Fetch content** from configured sources (RSS, sitemap, HTML)
2. **Parse** URLs and metadata
3. **Normalize** URLs (remove tracking parameters, lowercase, strip www)
4. **Deduplicate** URLs within collection batch
5. **Store** raw items in database
6. **Handle errors** gracefully (failed sources don't block others)

### External Dependencies
- `feedparser` for RSS parsing
- `requests` for HTTP fetching
- `BeautifulSoup` for HTML parsing
- `lxml` for XML/sitemap parsing

### Configuration
Loaded from `config/feeds.yaml`:
```yaml
feeds:
  - name: "NZZ"
    type: "rss"
    url: "https://www.nzz.ch/recent.rss"
    priority: 3
    max_age_hours: 24
    rate_limit_seconds: 2

  - name: "FINMA"
    type: "rss"
    url: "https://www.finma.ch/en/news/rss/"
    priority: 1
    max_age_hours: 168  # 7 days

  - name: "20 Minuten"
    type: "sitemap"
    url: "https://www.20min.ch/sitemap-news.xml"
    priority: 3
    max_age_hours: 24
```

### Error Handling
```python
class CollectionError(Exception):
    """Base exception for collection errors"""

class FeedUnavailableError(CollectionError):
    """Feed returned non-200 status or timeout"""

class FeedParseError(CollectionError):
    """Feed content could not be parsed"""

# Strategy: Log error, continue with other feeds
# Failed feeds reported in summary, don't fail pipeline
```

### Performance Considerations
- **Parallel fetching**: Fetch multiple feeds concurrently (respect rate limits)
- **Timeout enforcement**: 10 seconds per feed request
- **Connection pooling**: Reuse HTTP connections
- **Early filtering**: Skip articles older than max_age_hours immediately

### Success Metrics
- All configured feeds processed (or errors logged)
- Duplicate URLs eliminated within batch
- Processing time <30 seconds for 15 feeds
- URL normalization 100% consistent

### Testing Strategy
- Unit tests with mocked HTTP responses
- Feed parser tests with sample RSS/sitemap/HTML
- URL normalization tests (edge cases: redirects, parameters, fragments)
- Error handling tests (timeout, malformed feed, 404)

---

## Module 2: ContentFilter

### Purpose
Classify articles by relevance to Creditreform's credit risk focus using AI, processing only title and URL (not full content).

### Interface

**Input**:
```python
@dataclass
class ArticleMetadata:
    # ... (from Module 1)
```

**Output**:
```python
@dataclass
class FilteredArticle:
    # All fields from ArticleMetadata, plus:
    is_match: bool
    confidence: float  # 0.0 to 1.0
    topic: str  # "creditreform_insights", etc.
    reason: str  # Brief classification explanation
    filtered_at: datetime
```

### Responsibilities
1. **Check cache** for previously classified URLs (avoid redundant API calls)
2. **Batch articles** for efficient API processing
3. **Call OpenAI API** with title + URL only (NOT full content!)
4. **Parse classification** response (is_match, confidence, topic, reason)
5. **Filter by threshold** (confidence >= 0.71)
6. **Store classifications** for future cache hits
7. **Track costs** (token usage, API calls)

### External Dependencies
- OpenAI API (gpt-5-nano for cost efficiency)
- Repository layer for cache lookups

### Classification Prompt Structure
```python
SYSTEM_PROMPT = """
You are a Swiss financial analyst specializing in credit risk assessment for Creditreform.

Focus areas:
- Credit ratings and risk (Bonität, Rating, Kreditwürdigkeit)
- Insolvency and bankruptcy (Konkurs, Insolvenz, Zahlungsunfähigkeit)
- Regulatory compliance (FINMA, Basel III, nDSG, SchKG)
- Payment behavior (Zahlungsmoral, Zahlungsverzug, Inkasso)
- Market intelligence (KMU Finanzierung, Kreditversicherung)
"""

USER_PROMPT_TEMPLATE = """
Title: {title}
URL: {url}
Source: {source}

Is this article relevant to Creditreform's credit risk and business intelligence focus?

Respond in JSON:
{{
  "match": boolean,
  "conf": float,  // 0.0-1.0
  "topic": string,  // e.g., "creditreform_insights"
  "reason": string  // 1 sentence, max 100 chars
}}
"""
```

### Batching Strategy
```python
BATCH_SIZE = 50  # Articles per batch request
BATCH_WINDOW_HOURS = 1  # Wait up to 1 hour for batch completion

# Use OpenAI Batch API for 50% cost savings
batch = await openai.batches.create(
    input_file=batch_file_id,
    endpoint="/v1/chat/completions",
    completion_window="24h"
)
```

### Caching Strategy
**Exact Match Cache**:
```python
cache_key = hashlib.sha256(f"{title}|{url}".encode()).hexdigest()

# Check cache (7-day TTL)
cached = repo.get_classification(cache_key, max_age_days=7)
if cached:
    return cached  # Skip API call
```

**Semantic Cache** (optional, advanced):
```python
embedding = embed_model.encode(title)
similar = vector_db.search(embedding, threshold=0.85)
if similar:
    return similar.classification  # Reuse similar article's classification
```

### Error Handling
```python
class FilterError(Exception):
    """Base exception for filtering errors"""

class APIError(FilterError):
    """OpenAI API returned error"""

class ValidationError(FilterError):
    """Classification response failed validation"""

# Strategy: Retry with exponential backoff (max 3 attempts)
# If batch fails, fallback to individual API calls
# If all retries fail, log error and skip article (don't block pipeline)
```

### Performance Considerations
- **Batching**: Process 50 articles per API call (50% cost savings)
- **Caching**: 70%+ cache hit rate reduces API calls
- **Parallel processing**: Multiple batches in parallel (within rate limits)
- **Early exit**: Skip obviously irrelevant articles with simple keyword filter

### Cost Optimization
- Title/URL only: **90% cost reduction** vs. full content
- Batching: **50% API cost reduction**
- Caching: **15-30% additional savings**
- Target: <$0.05 per article classification

### Success Metrics
- Classification accuracy >85% (validated against golden dataset)
- Cache hit rate >70%
- Processing time <2 minutes for 100 articles (batched)
- Cost per classification <$0.05
- API error rate <1%

### Testing Strategy
- Unit tests with mocked OpenAI responses
- Integration tests with real API (rate limited)
- Golden dataset for accuracy validation (50 hand-labeled articles)
- Cost tracking tests (ensure batching and caching work)

---

## Module 3: ContentScraper

### Purpose
Extract full article content from web pages using multiple strategies (Trafilatura, Playwright fallback).

### Interface

**Input**:
```python
@dataclass
class FilteredArticle:
    # ... (from Module 2)
```

**Output**:
```python
@dataclass
class ScrapedArticle:
    # All fields from FilteredArticle, plus:
    content: str  # Full article text
    author: Optional[str]
    content_length: int  # Character count
    extraction_method: Literal["trafilatura", "playwright", "json_ld"]
    extraction_quality: float  # 0.0-1.0 quality score
    scraped_at: datetime
```

### Responsibilities
1. **Attempt Trafilatura** extraction first (fast, 70-85% success)
2. **Fallback to Playwright** if Trafilatura fails (slow, 95% success)
3. **Attempt JSON-LD** extraction for structured data
4. **Validate content** quality (length, structure)
5. **Handle errors** gracefully (timeouts, 404s, paywalls)
6. **Store content** in database
7. **Respect rate limits** (max 10 concurrent requests per domain)

### External Dependencies
- `trafilatura` for content extraction
- `playwright` for browser automation (fallback)
- `requests` for HTTP fetching
- BeautifulSoup for JSON-LD parsing

### Extraction Strategy

**Primary: Trafilatura** (fast, 70-85% success)
```python
import trafilatura

def extract_with_trafilatura(url: str) -> Optional[str]:
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None

    content = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=True,
        include_formatting=False,
        favor_recall=True  # High recall for Swiss news sites
    )

    return content
```

**Fallback: Playwright** (slow, 95% success)
```python
from playwright.async_api import async_playwright

async def extract_with_playwright(url: str) -> Optional[str]:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto(url, timeout=12000)
            await page.wait_for_load_state("networkidle", timeout=12000)

            # Handle cookie consent (common on Swiss news sites)
            await click_cookie_consent(page)

            # Extract main content
            content = await page.evaluate("""() => {
                const article = document.querySelector('article') ||
                                 document.querySelector('.article-content') ||
                                 document.querySelector('main');
                return article ? article.innerText : null;
            }""")

            return content
        finally:
            await browser.close()
```

**JSON-LD Extraction** (structured data)
```python
def extract_json_ld(html: str) -> Optional[Dict]:
    soup = BeautifulSoup(html, 'html.parser')
    scripts = soup.find_all('script', type='application/ld+json')

    for script in scripts:
        try:
            data = json.loads(script.string)
            if data.get('@type') == 'NewsArticle':
                return {
                    'title': data.get('headline'),
                    'author': data.get('author', {}).get('name'),
                    'published': data.get('datePublished'),
                    'content': data.get('articleBody')
                }
        except json.JSONDecodeError:
            continue

    return None
```

### Quality Scoring
```python
def calculate_quality_score(content: str, method: str) -> float:
    score = 1.0

    # Penalize very short content
    if len(content) < 200:
        score *= 0.3
    elif len(content) < 500:
        score *= 0.7

    # Penalize low word-to-char ratio (indicates non-text content)
    words = len(content.split())
    if words < 50:
        score *= 0.5

    # Bonus for Trafilatura (generally higher quality)
    if method == "trafilatura":
        score *= 1.1

    # Penalize Playwright fallback (sometimes captures nav/footer)
    if method == "playwright":
        score *= 0.9

    return min(score, 1.0)
```

### Error Handling
```python
class ScrapingError(Exception):
    """Base exception for scraping errors"""

class TimeoutError(ScrapingError):
    """Page load timeout"""

class PaywallError(ScrapingError):
    """Content behind paywall"""

class NotFoundError(ScrapingError):
    """404 or page not found"""

# Strategy:
# 1. Try Trafilatura (timeout: 5s)
# 2. Try Playwright (timeout: 12s)
# 3. If both fail, log error and mark article as "scraping_failed"
# 4. Continue with other articles (don't block pipeline)
```

### Performance Considerations
- **Parallel scraping**: 10-20 concurrent requests
- **Connection pooling**: Reuse HTTP connections
- **Timeout enforcement**: 5s for Trafilatura, 12s for Playwright
- **Rate limiting**: Max 2 requests/second per domain
- **Caching**: Never re-scrape same URL (check database first)

### Success Metrics
- Extraction success rate >90%
- Trafilatura success rate >70% (prefer fast path)
- Average extraction time <2 seconds (Trafilatura), <8 seconds (Playwright)
- Content quality score >0.7 for 80% of articles
- Zero crashes from malformed HTML

### Testing Strategy
- Unit tests with saved HTML fixtures
- Integration tests with live URLs (sample from each source)
- Timeout tests (ensure hard limits enforced)
- Quality score validation (edge cases: short articles, image galleries)

---

## Module 4: ArticleSummarizer

### Purpose
Generate concise, structured summaries of articles with entity extraction, optimized for Swiss business context.

### Interface

**Input**:
```python
@dataclass
class ScrapedArticle:
    # ... (from Module 3)
```

**Output**:
```python
@dataclass
class SummarizedArticle:
    # All fields from ScrapedArticle, plus:
    summary_title: str  # Normalized title
    summary: str  # 150-200 word summary
    key_points: List[str]  # 3-6 bullet points
    entities: EntityData
    summarized_at: datetime

@dataclass
class EntityData:
    companies: List[str]
    people: List[str]
    locations: List[str]
    topics: List[str]
```

### Responsibilities
1. **Batch articles** for efficient summarization
2. **Call OpenAI API** with full content + Swiss business context
3. **Parse structured response** (summary, key_points, entities)
4. **Validate output** quality (length, completeness)
5. **Store summaries** in database
6. **Track costs** (token usage, API calls)

### Summarization Prompt Structure
```python
SYSTEM_PROMPT = """
You are a Swiss financial analyst creating concise summaries for credit risk professionals.

Focus on:
- Financial impacts and market implications
- Key stakeholders (companies, people)
- Regulatory/legal developments
- Credit risk signals (payment issues, insolvency, rating changes)
- Strategic business decisions
"""

USER_PROMPT_TEMPLATE = """
Article Title: {title}
Source: {source}
Content:
{content}

Create a structured summary for Swiss credit risk analysts.

Respond in JSON:
{{
  "title": string,  // Normalized headline (max 100 chars)
  "summary": string,  // 150-200 words, focus on credit implications
  "key_points": [string],  // 3-6 bullet points, most critical info
  "entities": {{
    "companies": [string],  // Company names mentioned
    "people": [string],  // Key people (executives, officials)
    "locations": [string],  // Geographic locations
    "topics": [string]  // Key themes (e.g., "Insolvenz", "Basel III")
  }}
}}
"""
```

### Batching Strategy
```python
BATCH_SIZE = 20  # Articles per batch (smaller than filtering due to longer prompts)

# Use OpenAI Batch API for 50% cost savings
batch = await openai.batches.create(
    input_file=batch_file_id,
    endpoint="/v1/chat/completions",
    completion_window="24h"
)
```

### Content Preparation
```python
def prepare_content(article: ScrapedArticle) -> str:
    content = article.content

    # Truncate if too long (save tokens)
    MAX_CHARS = 12000  # ~3000 tokens
    if len(content) > MAX_CHARS:
        content = content[:MAX_CHARS] + "... [truncated]"

    # Remove excessive whitespace
    content = ' '.join(content.split())

    return content
```

### Error Handling
```python
class SummarizationError(Exception):
    """Base exception for summarization errors"""

class APIError(SummarizationError):
    """OpenAI API returned error"""

class ValidationError(SummarizationError):
    """Summary response failed validation"""

# Strategy: Retry with exponential backoff (max 3 attempts)
# If batch fails, fallback to individual API calls
# If all retries fail, create fallback summary (first 200 words + title)
```

### Quality Validation
```python
def validate_summary(summary_data: Dict) -> bool:
    # Title present and reasonable length
    if not summary_data.get('title') or len(summary_data['title']) > 150:
        return False

    # Summary in expected range
    summary = summary_data.get('summary', '')
    word_count = len(summary.split())
    if word_count < 50 or word_count > 300:
        return False

    # At least 2 key points
    if len(summary_data.get('key_points', [])) < 2:
        return False

    # Entities present (at least one category non-empty)
    entities = summary_data.get('entities', {})
    total_entities = sum(len(v) for v in entities.values())
    if total_entities < 1:
        return False

    return True
```

### Performance Considerations
- **Batching**: Process 20 articles per batch (50% cost savings)
- **Content truncation**: Limit to 12K chars (save tokens, maintain quality)
- **Temperature=0**: Deterministic outputs (easier caching)
- **Parallel batches**: Multiple batches in parallel (within rate limits)

### Cost Optimization
- Batching: **50% cost reduction**
- Content truncation: **20-30% token savings**
- Target: <$0.20 per article summary

### Success Metrics
- Summary quality score >4/5 (human evaluation on sample)
- Entity extraction accuracy >80% (validated on golden dataset)
- Processing time <3 minutes for 15 articles (batched)
- Cost per summary <$0.20
- Validation pass rate >95%

### Testing Strategy
- Unit tests with mocked OpenAI responses
- Integration tests with real API (sample articles)
- Quality validation tests (ensure outputs meet criteria)
- Golden dataset for entity extraction accuracy
- Human evaluation on random sample (monthly)

---

## Module 5: DigestGenerator

### Purpose
Create daily digest reports by analyzing summaries, deduplicating stories, and generating meta-insights in German.

### Interface

**Input**:
```python
@dataclass
class SummarizedArticle:
    # ... (from Module 4)

@dataclass
class DigestState:
    date: date
    articles: List[SummarizedArticle]  # Articles from previous runs today
    version: int  # Incremental version number
```

**Output**:
```python
@dataclass
class DailyDigest:
    date: date
    version: int
    articles: List[SummarizedArticle]  # Deduplicated, prioritized
    meta_analysis: MetaAnalysis
    generated_at: datetime

@dataclass
class MetaAnalysis:
    key_themes: List[str]  # Top 3-5 themes across articles
    credit_risk_signals: List[str]  # Notable risk indicators
    regulatory_updates: List[str]  # Regulatory/legal changes
    market_insights: List[str]  # Broader market intelligence
```

### Responsibilities
1. **Load existing digest** for current day (incremental updates)
2. **Deduplicate articles** across sources (same story from multiple outlets)
3. **Prioritize articles** by source authority and relevance
4. **Generate meta-analysis** (themes, trends, insights)
5. **Format outputs** (JSON, Markdown, German rating report)
6. **Save digest state** for next run

### Deduplication Strategy

**GPT-Based Clustering**:
```python
async def deduplicate_articles(articles: List[SummarizedArticle]) -> List[ArticleCluster]:
    # Group by similarity
    clusters = []

    for article in articles:
        # Check if article belongs to existing cluster
        placed = False

        for cluster in clusters:
            similarity = await check_similarity(article, cluster.primary_article)

            if similarity > 0.85:  # High similarity threshold
                cluster.add_duplicate(article)
                placed = True
                break

        if not placed:
            # Create new cluster
            clusters.append(ArticleCluster(primary_article=article))

    return clusters

async def check_similarity(article1: SummarizedArticle, article2: SummarizedArticle) -> float:
    prompt = f"""
    Are these two articles about the same story?

    Article 1:
    Title: {article1.summary_title}
    Summary: {article1.summary[:200]}

    Article 2:
    Title: {article2.summary_title}
    Summary: {article2.summary[:200]}

    Respond with similarity score 0.0-1.0:
    0.0 = completely different stories
    1.0 = identical story, same event
    """

    response = await openai.complete(prompt, temperature=0)
    return float(response.strip())
```

**Primary Article Selection** (from cluster):
1. Source priority (government > financial > general)
2. Content quality score
3. Publication recency
4. Content length (longer usually better)

### Incremental Digest Updates

```python
def update_digest(current_digest: Optional[DailyDigest],
                 new_articles: List[SummarizedArticle]) -> DailyDigest:

    if current_digest is None:
        # First run today, create new digest
        return create_new_digest(new_articles)

    # Merge new articles with existing
    all_articles = current_digest.articles + new_articles

    # Deduplicate combined set
    clusters = deduplicate_articles(all_articles)
    deduplicated = [cluster.primary_article for cluster in clusters]

    # Regenerate meta-analysis with full article set
    meta_analysis = generate_meta_analysis(deduplicated)

    return DailyDigest(
        date=current_digest.date,
        version=current_digest.version + 1,
        articles=deduplicated,
        meta_analysis=meta_analysis,
        generated_at=datetime.now()
    )
```

### Meta-Analysis Generation

```python
async def generate_meta_analysis(articles: List[SummarizedArticle]) -> MetaAnalysis:
    # Prepare article summaries for analysis
    article_texts = [
        f"{a.summary_title}\n{a.summary}\nTopics: {', '.join(a.entities.topics)}"
        for a in articles
    ]

    prompt = f"""
    Analyze these {len(articles)} Swiss business news summaries and provide meta-insights.

    Articles:
    {chr(10).join(article_texts)}

    Generate strategic insights for credit risk professionals:

    1. Key Themes (3-5): Dominant topics across articles
    2. Credit Risk Signals (2-4): Notable bankruptcy, insolvency, payment issues
    3. Regulatory Updates (0-3): FINMA, Basel III, legal changes
    4. Market Insights (2-4): Broader economic/market implications

    Respond in JSON (German language):
    {{
      "key_themes": [string],
      "credit_risk_signals": [string],
      "regulatory_updates": [string],
      "market_insights": [string]
    }}
    """

    response = await openai.complete(prompt, temperature=0.3)
    return MetaAnalysis(**json.loads(response))
```

### Output Formatting

**JSON Digest**:
```json
{
  "date": "2026-01-04",
  "version": 3,
  "articles": [
    {
      "title": "...",
      "summary": "...",
      "key_points": ["...", "..."],
      "entities": {...},
      "source": "NZZ",
      "url": "..."
    }
  ],
  "meta_analysis": {
    "key_themes": ["..."],
    "credit_risk_signals": ["..."],
    "regulatory_updates": ["..."],
    "market_insights": ["..."]
  }
}
```

**German Rating Report** (Jinja2 template):
```markdown
# Bonitäts-Tagesanalyse – {{ date.strftime('%d.%m.%Y') }}

## Überblick
{{ meta_analysis.key_themes | join(', ') }}

## Kreditrisiko-Signale
{% for signal in meta_analysis.credit_risk_signals %}
- {{ signal }}
{% endfor %}

## Regulatorische Entwicklungen
{% for update in meta_analysis.regulatory_updates %}
- {{ update }}
{% endfor %}

## Artikel ({{ articles | length }})
{% for article in articles %}
### {{ article.summary_title }}
**Quelle:** {{ article.source }}
**Link:** {{ article.url }}

{{ article.summary }}

**Kernpunkte:**
{% for point in article.key_points %}
- {{ point }}
{% endfor %}

**Relevante Unternehmen:** {{ article.entities.companies | join(', ') }}
{% endfor %}
```

### Error Handling
```python
class DigestError(Exception):
    """Base exception for digest generation errors"""

class DeduplicationError(DigestError):
    """Error during article deduplication"""

class MetaAnalysisError(DigestError):
    """Error generating meta-analysis"""

# Strategy: If deduplication fails, skip it (include all articles)
# If meta-analysis fails, use template-based fallback (no LLM)
# Always produce output, even if degraded quality
```

### Performance Considerations
- **Incremental updates**: Only analyze new articles, not full regeneration
- **Template-based formatting**: Minimize LLM usage for output formatting
- **Deduplication caching**: Cache similarity checks between runs
- **Parallel similarity checks**: Check multiple pairs concurrently

### Cost Optimization
- Incremental updates: **75% cost reduction** vs. full regeneration
- Template-based formatting: **90% reduction** vs. LLM-generated reports
- Deduplication caching: **50% reduction** in similarity API calls
- Target: <$0.10 per digest update

### Success Metrics
- Deduplication accuracy >90% (same stories grouped correctly)
- Meta-analysis relevance >4/5 (human evaluation)
- Processing time <1 minute for digest update
- Cost per digest <$0.10
- Report quality score >4/5 (analyst feedback)

### Testing Strategy
- Unit tests with sample articles
- Deduplication tests with known duplicates
- Meta-analysis quality validation (human review)
- Template rendering tests
- End-to-end integration tests

---

## Module Integration & Orchestration

### Orchestrator Responsibilities
1. **Load configuration** (feeds, topics, prompts, environment)
2. **Initialize modules** with dependencies (repositories, API clients)
3. **Execute pipeline** in sequence
4. **Handle errors** at module boundaries
5. **Manage state** (track progress, enable resume)
6. **Report progress** (logging, metrics)

### Orchestration Pattern

```python
class PipelineOrchestrator:
    def __init__(self, config: Config):
        self.config = config
        self.modules = self._init_modules()
        self.state = PipelineState()

    async def run(self):
        try:
            # Module 1: Collect
            collected = await self.modules.collector.collect(self.config.feeds)
            self.state.collected_count = len(collected)

            # Module 2: Filter
            filtered = await self.modules.filter.filter(collected)
            self.state.filtered_count = len(filtered)

            # Module 3: Scrape
            scraped = await self.modules.scraper.scrape(filtered)
            self.state.scraped_count = len(scraped)

            # Module 4: Summarize
            summarized = await self.modules.summarizer.summarize(scraped)
            self.state.summarized_count = len(summarized)

            # Module 5: Digest
            digest = await self.modules.digest_generator.generate(
                summarized,
                self.state.current_digest
            )
            self.state.digest_version = digest.version

            return digest

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self.state.error = str(e)
            raise
```

### Error Recovery

**Resume from Failure**:
```python
# Each module checks database for existing results
# Skip already-processed items on resume

def resume_pipeline(run_id: str):
    state = load_pipeline_state(run_id)

    if state.stage == "collected":
        # Resume from filtering
        collected = load_collected_articles(run_id)
        return run_from_filter(collected, state)

    elif state.stage == "filtered":
        # Resume from scraping
        filtered = load_filtered_articles(run_id)
        return run_from_scraper(filtered, state)

    # ... etc
```

**Graceful Degradation**:
```python
# If a module fails, continue with partial results
# Log error, produce degraded output, don't fail entire pipeline

try:
    summarized = await summarizer.summarize(scraped)
except SummarizationError as e:
    logger.error(f"Summarization failed: {e}")
    # Use fallback: first 200 words as summary
    summarized = create_fallback_summaries(scraped)
```

### Progress Tracking

```python
@dataclass
class PipelineState:
    run_id: str
    started_at: datetime
    stage: str  # "collecting", "filtering", etc.
    collected_count: int = 0
    filtered_count: int = 0
    scraped_count: int = 0
    summarized_count: int = 0
    digest_version: int = 0
    error: Optional[str] = None

# Update state after each module
# Store in database for resume capability
# Report progress to user/logging
```

## Plugin Architecture (Future Extension)

### Collector Plugins
Enable adding new news sources without modifying core code:
```python
class CollectorPlugin(Protocol):
    def collect(self, config: FeedConfig) -> List[ArticleMetadata]:
        ...

# Plugins:
# - GoogleNewsCollectorPlugin
# - TwitterCollectorPlugin
# - NewsAPICollectorPlugin
```

### Analyzer Plugins
Enable custom analysis beyond standard pipeline:
```python
class AnalyzerPlugin(Protocol):
    def analyze(self, articles: List[SummarizedArticle]) -> AnalysisResult:
        ...

# Plugins:
# - SentimentAnalyzerPlugin
# - TrendDetectionPlugin
# - CompanyMonitoringPlugin
```

## Conclusion

The modular pipeline design enables:
- **Independent development** and testing of each component
- **Clear interfaces** for predictable behavior
- **Easy debugging** (isolate failures to specific modules)
- **Flexible optimization** (improve modules independently)
- **Future extensibility** (plugin architecture for new sources/analyzers)

**Next Steps**:
- Review database design (04-database-design.md)
- Understand data models and schemas (11-data-models-schemas.md)
- Begin implementation with Module 1 (NewsCollector)
