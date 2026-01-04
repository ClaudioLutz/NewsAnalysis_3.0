# System Architecture & Design

## Overview

The NewsAnalysis system is an AI-powered business intelligence platform that transforms high-volume Swiss business news into actionable credit risk insights for Creditreform Switzerland. This document outlines the architectural principles, design patterns, and system structure for a clean, modular rebuild optimized for cost-efficiency and local deployment.

## Value Proposition

**Problem**: Creditreform analysts must manually review 100+ daily Swiss business articles to identify credit risk signals, regulatory changes, and market intelligence relevant to B2B credit assessment.

**Solution**: Automated AI pipeline that:
- Collects news from 15+ Swiss sources (RSS, sitemaps, HTML)
- Filters to 5-15 highly relevant articles (85% reduction)
- Generates German-language rating reports (Bonitäts-Tagesanalyse)
- Delivers actionable intelligence in <5 minutes daily

**Business Impact**:
- 90% time savings on news triage
- Zero missed critical credit signals
- Consistent quality analysis
- <$50/month operational cost target

## Core Architectural Principles

### 1. **Cost-First Design**
Every architectural decision prioritizes LLM API cost reduction:
- Title/URL filtering before expensive content scraping (90% cost reduction)
- Batch processing for 50% API cost savings
- Semantic caching for 15-30% additional savings
- Right-sized model selection (nano → mini → sonnet as needed)
- Token usage monitoring as first-class concern

### 2. **Modularity & Separation of Concerns**
Clear boundaries between system components:
- Independent pipeline modules with well-defined interfaces
- Repository pattern for data access abstraction
- Service layer for business logic
- Integration layer for external APIs
- Each module testable in isolation

### 3. **Local-First Deployment**
Optimized for single-server operation:
- SQLite for <100K articles (upgrade path to PostgreSQL)
- No distributed system complexity
- Minimal infrastructure dependencies
- Docker optional (not required)
- Windows/Linux compatible

### 4. **Reliability Over Performance**
Prioritize correctness and resilience:
- Graceful degradation when services fail
- Comprehensive error handling and logging
- State persistence for resumable execution
- Data validation at system boundaries
- Zero data loss guarantee

### 5. **Maintainability Over Clever Code**
Simple, readable, standard patterns:
- Explicit over implicit
- Composition over inheritance
- Boring technology choices
- Comprehensive type hints
- Self-documenting code structure

## System Architecture

### High-Level Component View

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI / Scheduler                          │
│              (Entry Point, Configuration)                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Pipeline Orchestrator                       │
│        (Coordinates modules, manages state)                  │
└────┬─────────┬──────────┬──────────┬──────────┬─────────────┘
     │         │          │          │          │
     ▼         ▼          ▼          ▼          ▼
┌─────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
│  News   │ │Content │ │Content │ │ Article  │ │ Digest   │
│Collector│ │Filter  │ │Scraper │ │Summarizer│ │Generator │
│ Module  │ │ Module │ │ Module │ │  Module  │ │  Module  │
└────┬────┘ └───┬────┘ └───┬────┘ └────┬─────┘ └────┬─────┘
     │          │          │           │            │
     └──────────┴──────────┴───────────┴────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   Repository Layer     │
              │  (Data Access Logic)   │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │   Database (SQLite)    │
              │  (Persistent Storage)  │
              └────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Cross-Cutting Concerns                          │
│  • Logging (Structured, JSON)                               │
│  • Cost Tracking (Token usage, API calls)                   │
│  • Configuration (YAML, .env)                               │
│  • Error Handling (Circuit breakers, retries)              │
└─────────────────────────────────────────────────────────────┘

External Integrations:
  • OpenAI API (GPT models for filtering/summarization)
  • News Sources (RSS, HTTP)
  • Cache Layer (Optional: Redis for distributed caching)
```

### Layer Architecture

**Presentation Layer** (CLI):
- Command-line interface for manual execution
- Scheduled execution via cron/Windows Task Scheduler
- Configuration management
- Output formatting

**Orchestration Layer**:
- Pipeline state management
- Module coordination
- Error recovery
- Progress tracking
- Performance monitoring

**Business Logic Layer** (Pipeline Modules):
- NewsCollector: Multi-source news aggregation
- ContentFilter: AI-based relevance classification
- ContentScraper: Web content extraction
- ArticleSummarizer: AI-powered summarization
- DigestGenerator: Meta-analysis and reporting

**Data Access Layer** (Repositories):
- Abstract database operations
- Query optimization
- Transaction management
- Cache integration
- Data validation

**Infrastructure Layer**:
- Database connection management
- External API clients (OpenAI, HTTP)
- Logging infrastructure
- Configuration loading
- File system operations

## Pipeline Architecture (5-Step Flow)

### Step 1: News Collection
**Module**: NewsCollector
**Input**: Feed configurations (YAML)
**Output**: List of article URLs with metadata

**Process**:
1. Load feed configurations (RSS, sitemap, HTML sources)
2. Fetch content from each source (parallel where safe)
3. Parse URLs and metadata (title, published date, source)
4. Normalize URLs (strip tracking parameters)
5. Deduplicate against existing database entries
6. Store raw items in database

**Optimization Points**:
- Source prioritization (government > financial > general)
- Time-based filtering (respect max article age)
- Rate limiting per source
- Fail-fast for broken sources

### Step 2: AI Filtering
**Module**: ContentFilter
**Input**: Article URLs + titles from Step 1
**Output**: Filtered list of relevant articles with confidence scores

**Process**:
1. Batch articles for processing (optimize API costs)
2. Check cache for previously classified URLs
3. Call GPT-nano with title + URL only (no content!)
4. Parse structured response (is_match, confidence, topic, reason)
5. Filter by confidence threshold (0.71+)
6. Store classifications in database

**Optimization Points**:
- **CRITICAL**: Title/URL only (90% cost reduction)
- Batch API calls (50% additional cost savings)
- Semantic cache for similar titles (15-30% savings)
- Parallel processing within rate limits
- Skip URLs processed in recent runs

### Step 3: Content Scraping
**Module**: ContentScraper
**Input**: Filtered article URLs from Step 2
**Output**: Full article content (text, metadata)

**Process**:
1. Attempt extraction with Trafilatura (fast, 70-85% success)
2. Fallback to Playwright for JS-heavy sites (slower, 95% success)
3. Extract article metadata (author, date, content)
4. Score content quality (length, structure, completeness)
5. Store article content in database

**Optimization Points**:
- Parallel scraping with connection pooling
- Timeout enforcement (12 seconds max per article)
- Cache scraped content (never re-scrape same URL)
- Skip scraping if content already exists

### Step 4: Article Summarization
**Module**: ArticleSummarizer
**Input**: Full article content from Step 3
**Output**: Structured summaries (title, summary, key points, entities)

**Process**:
1. Batch articles for summarization
2. Check cache for previously summarized content
3. Call GPT-mini with article content + Swiss business context
4. Parse structured response (summary, key_points, entities)
5. Validate entity extraction quality
6. Store summaries in database

**Optimization Points**:
- Batch processing (50% cost savings)
- Content fingerprinting (cache similar articles)
- Prompt optimization (token-efficient instructions)
- Temperature=0 for deterministic outputs

### Step 5: Digest Generation
**Module**: DigestGenerator
**Input**: Summaries from Step 4, previous digest state
**Output**: Daily digest (JSON, Markdown, German report)

**Process**:
1. Load existing digest for current day (incremental updates)
2. Deduplicate stories across sources (GPT-based clustering)
3. Prioritize articles by relevance and source authority
4. Generate meta-analysis (themes, trends, insights)
5. Format outputs (JSON, Markdown, German rating report)
6. Save digest and update state

**Optimization Points**:
- Incremental digest updates (not full regeneration)
- Smart deduplication (avoid duplicate LLM calls)
- Template-based formatting (minimize LLM usage)
- Cache digest fragments

## Design Patterns

### 1. **Pipeline Pattern**
Sequential stages with clear inputs/outputs:
```python
result1 = collector.collect()
result2 = filter.filter(result1)
result3 = scraper.scrape(result2)
result4 = summarizer.summarize(result3)
result5 = digest_generator.generate(result4)
```

**Benefits**:
- Easy to understand and debug
- Testable stages
- Clear failure points
- Resumable execution

### 2. **Repository Pattern**
Abstract data access behind interfaces:
```python
class ArticleRepository:
    def save(article: Article) -> None
    def find_by_url(url: str) -> Optional[Article]
    def find_unprocessed() -> List[Article]
```

**Benefits**:
- Database-agnostic business logic
- Centralized query optimization
- Easy to mock for testing
- Migration path to PostgreSQL

### 3. **Strategy Pattern**
Swappable implementations for different approaches:
```python
class ContentExtractor(Protocol):
    def extract(url: str) -> Optional[Content]

# Implementations: TrafilaturaExtractor, PlaywrightExtractor
```

**Benefits**:
- Easy to add new extractors
- A/B testing different approaches
- Fallback chains
- Independent testing

### 4. **Factory Pattern**
Centralized object creation:
```python
class ModuleFactory:
    def create_collector(config: Config) -> NewsCollector
    def create_filter(config: Config) -> ContentFilter
```

**Benefits**:
- Dependency injection
- Configuration-driven behavior
- Consistent initialization
- Easier testing with mocks

### 5. **Circuit Breaker Pattern**
Prevent cascading failures:
```python
class CircuitBreaker:
    # Temporarily disable failing external services
    # Auto-recovery after cooldown period
```

**Benefits**:
- Graceful degradation
- Faster failure detection
- Resource protection
- Better error messages

## Separation of Concerns

### Data Access (Repository Layer)
**Responsibilities**:
- Execute database queries
- Map database rows to domain objects
- Handle transactions
- Optimize query performance

**NOT Responsible For**:
- Business logic decisions
- API calls
- Data transformation beyond ORM mapping

### Business Logic (Service Layer)
**Responsibilities**:
- Implement domain rules
- Coordinate between modules
- Data validation and transformation
- Error handling and recovery

**NOT Responsible For**:
- Direct database access
- HTTP requests
- File I/O

### AI Orchestration (Pipeline Modules)
**Responsibilities**:
- Call AI APIs with correct prompts
- Parse and validate AI responses
- Implement retry logic
- Track token usage

**NOT Responsible For**:
- Storing results (delegates to repository)
- Complex business logic beyond AI coordination

## Technology Decision Rationale

### Python 3.11+
**Why**:
- Excellent library ecosystem for web scraping and AI
- Type hints for better code quality
- Performance improvements in 3.11+
- Wide team familiarity

**Trade-offs**:
- GIL limits true parallelism (mitigated with async I/O)
- Slower than compiled languages (not a concern for I/O-bound workload)

### SQLite (with PostgreSQL migration path)
**Why**:
- Zero configuration for local deployment
- Excellent for <100K articles
- ACID compliance and reliability
- Built-in full-text search (FTS5)
- Easy backup (single file)

**Trade-offs**:
- Limited concurrency (single writer)
- Not suitable for distributed deployment
- Migration to PostgreSQL when scaling needed

**Migration Trigger**: >100K articles OR need for >10 concurrent users

### OpenAI API
**Why**:
- State-of-art AI quality
- Structured output support
- Batch API for cost savings
- No model hosting complexity

**Trade-offs**:
- Ongoing API costs (mitigated with aggressive optimization)
- External dependency (requires internet)
- Rate limits (manageable with batching)

## Scalability Considerations for Local Deployment

### Current Design Targets
- **Volume**: 100-500 articles/day
- **Processing Time**: <5 minutes for daily run
- **Storage**: <10GB/year (with retention policies)
- **Cost**: <$50/month for OpenAI API
- **Concurrency**: Single-threaded pipeline (adequate for volume)

### Scaling Dimensions

**Vertical Scaling** (increase server resources):
- More memory → larger batch sizes
- Faster CPU → quicker content extraction
- SSD storage → faster database operations
- **Cost**: $0-50/month for modest VPS

**Horizontal Scaling** (future consideration):
- Migrate to PostgreSQL for multi-reader support
- Add Redis for distributed caching
- Separate scraping service (most time-consuming)
- Queue-based architecture (Celery + Redis)
- **Trigger**: >1000 articles/day OR <5 min processing not achievable

### Performance Optimization Levers

1. **Database Optimization**:
   - WAL mode for concurrent reads
   - Strategic indexing (url_hash, published_at, source)
   - Query result caching
   - Periodic VACUUM for compaction

2. **I/O Optimization**:
   - Connection pooling for HTTP requests
   - Parallel scraping (10-20 concurrent)
   - Async I/O for network operations
   - Content compression in database

3. **AI Optimization**:
   - Batch processing (primary lever)
   - Semantic caching (secondary lever)
   - Prompt optimization (reduce tokens)
   - Model right-sizing (nano/mini/sonnet)

## Modularity Benefits

### Independent Development
- Teams can work on modules in parallel
- Clear interfaces reduce coordination overhead
- Easier onboarding (understand one module at a time)

### Independent Testing
- Unit tests for individual modules
- Mock external dependencies easily
- Integration tests for module interactions
- End-to-end tests for complete pipeline

### Independent Deployment
- Update modules without full redeployment
- Feature flags for gradual rollout
- A/B testing of different implementations
- Easy rollback if issues arise

### Independent Scaling
- Identify bottlenecks at module level
- Optimize hot paths without affecting others
- Extract modules to separate services if needed
- Add caching at module boundaries

## Security Considerations

### API Key Management
- Never commit API keys to version control
- Use environment variables or secure vaults
- Rotate keys periodically
- Monitor usage for anomalies

### Data Privacy
- No PII collection (only public news)
- Secure storage of scraped content
- GDPR compliance for EU users (if applicable)
- Data retention policies

### External API Security
- Validate SSL certificates
- Implement request signing where available
- Rate limiting to prevent abuse
- Audit trail for all API calls

### Database Security
- Encrypted database file (optional)
- Access control for production systems
- Regular backups with encryption
- SQL injection prevention (parameterized queries)

## Monitoring & Observability

### Key Metrics
- **Cost Metrics**: Token usage, API calls, cost per article
- **Performance Metrics**: Pipeline duration, module latency, database query time
- **Quality Metrics**: Classification accuracy, extraction success rate, summary quality
- **Reliability Metrics**: Error rates, retry counts, circuit breaker trips

### Logging Strategy
- Structured logging (JSON format)
- Log levels: DEBUG (development), INFO (production), WARNING (issues), ERROR (failures)
- Correlation IDs for request tracing
- Sensitive data redaction

### Alerting Triggers
- Cost threshold exceeded (>$2/day)
- Pipeline failure (any module)
- Extraction success rate <50%
- Classification confidence drop >10%
- Database size approaching limits

## Conclusion

This architecture prioritizes **cost efficiency**, **modularity**, and **local deployment simplicity** while maintaining a clear path to scale. The design learns from the POC's successes (title/URL filtering, incremental digests) while introducing modern patterns for improved maintainability and testing.

**Next Steps**:
1. Review remaining documentation (02-12)
2. Understand LLM cost optimization strategies (critical)
3. Study modular pipeline design details
4. Begin implementation with Phase 1 (Foundation)
