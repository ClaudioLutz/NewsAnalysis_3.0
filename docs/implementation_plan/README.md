# NewsAnalysis 2.0 - Fresh Start Documentation

## Overview

This directory contains comprehensive strategic documentation for building an optimized, modular version of the NewsAnalysis system for creditreform.ch. The documentation is designed to enable an agent (or development team) to implement a production-ready news analysis system from scratch.

## Purpose

Transform the current proof-of-concept into a **cost-optimized, modular, production-ready system** for automated Swiss business news analysis, with the primary goal of **LLM cost reduction** and **local/on-premise deployment**.

## Target Metrics

- **Cost**: <$50/month for 100 articles/day
- **Performance**: <5 minutes for daily pipeline execution
- **Accuracy**: >85% classification accuracy
- **Quality**: >80% test coverage
- **Scalability**: Handle up to 500 articles/day on single server

## Documentation Structure

### Core Architecture (Read First)

**[01-system-architecture.md](01-system-architecture.md)** - Start Here
- System overview and value proposition
- Architectural principles (cost-first, modular, local-first)
- Component architecture and interactions
- Design patterns (Pipeline, Repository, Strategy, Factory, Circuit Breaker)
- Technology decision rationale
- Scalability considerations

**[02-llm-cost-optimization.md](02-llm-cost-optimization.md)** - Primary Focus
- Baseline cost analysis from POC
- Cost reduction strategies (50% from batching, 15-30% from caching, 90% from title/URL filtering)
- Implementation roadmap for cost optimization
- Real-time cost tracking and monitoring
- Budget enforcement and alerts
- **Target: <$50/month for 100 articles/day**

**[03-modular-pipeline-design.md](03-modular-pipeline-design.md)** - Pipeline Details
- Five pipeline modules with clear boundaries:
  1. NewsCollector - Multi-source aggregation
  2. ContentFilter - AI-based classification
  3. ContentScraper - Web content extraction
  4. ArticleSummarizer - AI summarization
  5. DigestGenerator - Meta-analysis and reporting
- Module interfaces and contracts
- Error handling and recovery
- Orchestration patterns

### Technical Foundation

**[04-database-design.md](04-database-design.md)** - Data Layer
- SQLite vs PostgreSQL decision matrix
- Complete database schema (articles, processed_links, pipeline_runs, api_calls, digests)
- Indexing strategy for performance
- Full-text search with FTS5
- Data retention policies (tiered by source priority)
- Backup and migration strategies

**[05-python-project-structure.md](05-python-project-structure.md)** - Code Organization
- Modern src layout (pytest/Nox compatible)
- Complete directory structure with rationale
- Module organization principles
- Dependency injection patterns
- pyproject.toml configuration
- Import conventions and best practices

**[06-api-integration-strategy.md](06-api-integration-strategy.md)** - External APIs
- OpenAI API client (async, retry, batch processing)
- News source integration (RSS, sitemaps, HTML)
- Rate limiting and throttling
- Circuit breaker pattern
- Error handling and fallbacks
- Cost tracking for all API calls

**[07-configuration-management.md](07-configuration-management.md)** - Config Strategy
- Environment variables (.env files)
- YAML configuration (feeds, topics, prompts)
- Secrets management
- Feature flags
- Multi-environment support (dev/staging/prod)
- Configuration validation with Pydantic

### Quality & Operations

**[08-testing-quality-assurance.md](08-testing-quality-assurance.md)** - Testing Strategy
- Testing pyramid (unit → integration → e2e)
- LLM testing strategies (mocks, golden datasets, VCR)
- Code quality tools (Ruff, Mypy, Pytest)
- Test fixtures and patterns
- Coverage targets (>80% overall, >90% critical paths)
- CI/CD pipeline configuration

**[09-deployment-operations.md](09-deployment-operations.md)** - Deployment Guide
- Deployment options (direct Python, Docker, systemd service)
- Scheduled execution (cron, Windows Task Scheduler)
- Logging strategy (structured JSON logs)
- Monitoring and health checks
- Backup automation
- Maintenance tasks (vacuum, cleanup, recovery)
- Troubleshooting guide

### Technology & Data

**[10-technology-stack.md](10-technology-stack.md)** - Tech Stack
- Core technologies (Python 3.11+, SQLite/PostgreSQL, OpenAI API)
- Key libraries with rationale:
  - Web scraping: trafilatura, playwright, feedparser
  - AI integration: openai, pydantic
  - Testing: pytest, ruff, mypy
- Avoided technologies and why
- Dependency management (pyproject.toml)
- Platform compatibility

**[11-data-models-schemas.md](11-data-models-schemas.md)** - Data Models
- Pydantic domain models (Article, Digest, Config)
- JSON schemas for AI responses (classification, summary, meta-analysis)
- Database models (SQLAlchemy)
- Validation examples
- Schema evolution strategy

**[12-implementation-phases.md](12-implementation-phases.md)** - Implementation Roadmap
- **6-week phased implementation plan**:
  - Week 1: Foundation (project setup, database, config)
  - Week 2: Pipeline Core (collector, filter)
  - Week 3: Content Processing (scraper, summarizer)
  - Week 4: Digest & Output (generator, formatters)
  - Week 5: Optimization (caching, cost monitoring)
  - Week 6: Production Readiness (testing, deployment, monitoring)
- Deliverables and success criteria per phase
- Risk mitigation strategies
- Definition of done

### Reference Data

**[13-swiss-news-sources.md](13-swiss-news-sources.md)** - Complete News Source Catalog
- **18 RSS feeds** with exact URLs (NZZ, Tamedia, SRF, FINMA, financial portals)
- **HTML sources** with CSS selectors (BusinessClass Ost)
- Source tiers and priority levels (government, financial, general)
- Integration patterns (RSS, sitemap, HTML parsing)
- Volume estimates and success rates
- Known issues and special handling (Tamedia partner feeds, Google News)
- Recommended configurations (MVP → Balanced → Maximum)
- Per-source implementation notes

## How to Use This Documentation

### For an Implementation Agent

**Step 1: Context Building**
1. Read [01-system-architecture.md](01-system-architecture.md) for overall system understanding
2. Read [02-llm-cost-optimization.md](02-llm-cost-optimization.md) for primary optimization goal
3. Read [03-modular-pipeline-design.md](03-modular-pipeline-design.md) for pipeline details

**Step 2: Technical Planning**
4. Review [04-database-design.md](04-database-design.md) for data layer
5. Review [05-python-project-structure.md](05-python-project-structure.md) for code organization
6. Review [10-technology-stack.md](10-technology-stack.md) for dependencies
7. Review [11-data-models-schemas.md](11-data-models-schemas.md) for data structures
8. Review [13-swiss-news-sources.md](13-swiss-news-sources.md) for exact feed URLs and integration

**Step 3: Implementation**
9. Follow [12-implementation-phases.md](12-implementation-phases.md) phase by phase
10. Reference [06-api-integration-strategy.md](06-api-integration-strategy.md) for external integrations
11. Reference [07-configuration-management.md](07-configuration-management.md) for config setup
12. Reference [13-swiss-news-sources.md](13-swiss-news-sources.md) for feed configurations

**Step 4: Quality & Deployment**
13. Implement tests per [08-testing-quality-assurance.md](08-testing-quality-assurance.md)
14. Deploy following [09-deployment-operations.md](09-deployment-operations.md)

### For Human Developers

**Quick Start**:
1. Read [README.md](README.md) (this file)
2. Read [01-system-architecture.md](01-system-architecture.md)
3. Read [12-implementation-phases.md](12-implementation-phases.md)
4. Start with Phase 1 (Foundation)

**Reference While Building**:
- Use topic-specific docs as needed
- Each document is self-contained
- Cross-references provided throughout

## Key Design Principles

### 1. Cost-First Design
Every architectural decision prioritizes LLM API cost reduction:
- Title/URL filtering before content scraping (90% cost reduction)
- Batch processing for 50% API cost savings
- Aggressive caching for 15-30% additional savings
- Right-sized model selection (nano → mini → sonnet)

### 2. Modularity
- Clear module boundaries with defined interfaces
- Independent testing and development
- Easy to extend and maintain
- Repository pattern for data access abstraction

### 3. Local-First Deployment
- SQLite for <100K articles (zero configuration)
- No distributed system complexity
- Minimal infrastructure dependencies
- Can run on single server or locally

### 4. Production Ready
- Comprehensive error handling
- Monitoring and alerting
- Automated backups
- Health checks
- Cost tracking from day one

## Research Sources

This documentation is based on industry best practices from:

**News Aggregation**:
- [How to Build a News Aggregator with Python](https://zencoder.ai/blog/how-to-build-a-news-aggregator-with-python)
- [Build a Content Aggregator in Python – Real Python](https://realpython.com/build-a-content-aggregator-python/)
- [ETL Pipelines in Python: Best Practices and Techniques](https://towardsdatascience.com/etl-pipelines-in-python-best-practices-and-techniques-0c148452cc68/)

**Modular AI Systems**:
- [Developer's guide to multi-agent patterns in ADK](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/)
- [Microservice Design Patterns for AI](https://dzone.com/articles/microservice-design-patterns-for-ai)
- [Microservices Architecture for AI Applications: 2025 Trends](https://medium.com/@meeran03/microservices-architecture-for-ai-applications-scalable-patterns-and-2025-trends-5ac273eac232)

**Python Project Structure**:
- [Best Practices in Structuring Python Projects](https://dagster.io/blog/python-project-best-practices)
- [Python Project Structure: Why the 'src' Layout Beats Flat Folders](https://medium.com/@adityaghadge99/python-project-structure-why-the-src-layout-beats-flat-folders-and-how-to-use-my-free-template-808844d16f35)
- [GitHub - johnthagen/python-blueprint](https://github.com/johnthagen/python-blueprint)

**LLM Cost Optimization**:
- [Batch Processing for LLM Cost Savings](https://www.prompts.ai/en/blog/batch-processing-for-llm-cost-savings)
- [How to Optimize Batch Processing for LLMs](https://latitude-blog.ghost.io/blog/how-to-optimize-batch-processing-for-llms/)
- [LLM Cost Optimization: Complete Guide to Reducing AI Expenses by 80% in 2025](https://ai.koombea.com/blog/llm-cost-optimization)

**Database Selection**:
- [SQLite vs PostgreSQL: A Detailed Comparison](https://www.datacamp.com/blog/sqlite-vs-postgresql-detailed-comparison)
- [SQLite or PostgreSQL? It's Complicated!](https://www.twilio.com/en-us/blog/sqlite-postgresql-complicated)
- [Appropriate Uses For SQLite](https://sqlite.org/whentouse.html)

## Success Criteria

The implementation is successful when:

**Cost Targets**:
- [x] Total monthly cost <$50 for 100 articles/day
- [x] Cost per processed article <$0.50
- [x] Classification cost <$0.05 per article
- [x] Cache hit rate >70%

**Performance Targets**:
- [x] Pipeline execution <5 minutes for daily run
- [x] Classification accuracy >85%
- [x] Scraping success rate >90%

**Quality Targets**:
- [x] Test coverage >80%
- [x] Modular architecture with <5 dependencies per module
- [x] Zero data loss (robust error handling)
- [x] Summary quality score >4/5

**Operational Targets**:
- [x] Automated daily execution
- [x] Monitoring and alerting configured
- [x] Automated backups working
- [x] Documentation complete

## Next Steps

1. **Review this README** to understand documentation structure
2. **Read architectural docs** (01-03) to understand system design
3. **Read technical docs** (04-11) to understand implementation details
4. **Follow implementation phases** (12) to build the system
5. **Validate against success criteria** throughout implementation

## Support & Feedback

For questions, clarifications, or issues:
- Review the specific documentation topic
- Check troubleshooting sections in deployment guide
- Refer to research sources for deeper understanding

## Version

Documentation Version: 1.0
Last Updated: 2026-01-04
Target System: NewsAnalysis 2.0 for creditreform.ch

---

**Ready to build a production-ready, cost-optimized news analysis system. Start with [01-system-architecture.md](01-system-architecture.md).**
