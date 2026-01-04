# Implementation Phases

## Overview

This document provides a phased implementation plan for building the NewsAnalysis system from scratch, optimized for incremental delivery and risk mitigation.

## Implementation Strategy

**Approach**: Vertical slicing - Build complete thin slices of functionality, not full layers.

**Principle**: Each phase delivers working software that can be tested and validated.

## Phase 1: Foundation (Week 1)

### Goals
- Establish project structure
- Set up development environment
- Initialize database
- Create core data models
- Implement basic CLI

### Deliverables

**1.1 Project Setup**
```bash
# Create project structure
mkdir -p src/newsanalysis/{cli,core,pipeline,database,services,utils}
mkdir -p tests/{unit,integration,fixtures}
mkdir -p config/{prompts}
mkdir -p scripts

# Initialize pyproject.toml
# Configure ruff, mypy, pytest
```

**1.2 Core Data Models**
- Implement Pydantic models (Article, ClassificationResult, etc.)
- Add validation logic
- Write unit tests for models

**1.3 Database Initialization**
- Create schema.sql (articles, processed_links, pipeline_runs, api_calls)
- Implement database connection management
- Write init_db.py script
- Add database migrations support

**1.4 Configuration Management**
- Implement Config class with environment loading
- Create .env.example template
- Add YAML config loading (feeds, topics, prompts)
- Write configuration validation tests

**1.5 Basic CLI**
- Create CLI entry point (Click)
- Implement `newsanalysis --version`
- Implement `newsanalysis --help`
- Add logging setup

### Success Criteria
- [ ] Project structure matches documentation
- [ ] Database initializes successfully
- [ ] All unit tests pass
- [ ] CLI runs without errors
- [ ] Configuration loads correctly

### Estimated Effort
40-60 hours (1 week full-time)

---

## Phase 2: Pipeline Core (Week 2)

### Goals
- Implement news collection (Module 1)
- Implement AI filtering (Module 2)
- Create repository layer
- End-to-end test for first 2 modules

### Deliverables

**2.1 News Collector Module**
- Implement RSSCollector
- Implement SitemapCollector
- Implement HTMLCollector (for Business Class Ost)
- Add URL normalization service
- Write unit tests with mocked feeds

**2.2 Article Repository**
- Implement ArticleRepository (save, find, update)
- Add database queries for article retrieval
- Implement connection pooling
- Write integration tests with test database

**2.3 AI Filter Module**
- Implement OpenAI client wrapper
- Create prompt builder for classification
- Implement classification logic (title/URL only)
- Add cost tracking
- Mock OpenAI responses in tests

**2.4 Pipeline Orchestrator (Basic)**
- Coordinate collector → filter flow
- Implement pipeline state tracking
- Add error handling
- Create run_id generation

**2.5 CLI Integration**
- Implement `newsanalysis run --limit 10` command
- Add progress logging
- Display statistics after run

### Success Criteria
- [ ] Can collect articles from 3 feed types
- [ ] Articles saved to database
- [ ] AI classification works (mocked in tests)
- [ ] End-to-end test: collect → filter
- [ ] Cost tracking records API calls

### Estimated Effort
40-60 hours (1 week full-time)

---

## Phase 3: Content Processing (Week 3)

### Goals
- Implement content scraping (Module 3)
- Implement article summarization (Module 4)
- Add OpenAI batch API support
- Complete pipeline orchestrator

### Deliverables

**3.1 Content Scraper Module**
- Implement TrafilaturaExtractor
- Implement PlaywrightExtractor (fallback)
- Add content quality scoring
- Implement extraction retry logic
- Write tests with saved HTML fixtures

**3.2 Article Summarizer Module**
- Implement summarization with OpenAI
- Create prompt builder for summaries
- Add entity extraction
- Implement batch processing
- Write tests with golden dataset

**3.3 OpenAI Batch API Integration**
- Implement batch job creation
- Add batch status polling
- Implement result retrieval
- Add error handling for batch failures

**3.4 Complete Pipeline Orchestrator**
- Integrate all 4 modules (collect → filter → scrape → summarize)
- Implement resume logic
- Add comprehensive error recovery
- Create pipeline state persistence

**3.5 Testing & Validation**
- End-to-end integration test (all 4 modules)
- Performance test (100 articles)
- Cost validation test

### Success Criteria
- [ ] Can scrape content with 90% success rate
- [ ] Summaries generated with quality validation
- [ ] Batch API works (50% cost savings)
- [ ] End-to-end pipeline runs successfully
- [ ] Processing time <5 minutes for 100 articles

### Estimated Effort
40-60 hours (1 week full-time)

---

## Phase 4: Digest Generation & Output (Week 4)

### Goals
- Implement digest generator (Module 5)
- Add deduplication logic
- Create output formatters
- Generate German rating reports

### Deliverables

**4.1 Digest Generator Module**
- Implement incremental digest updates
- Add article deduplication (GPT-based)
- Create meta-analysis generation
- Implement digest state management

**4.2 Output Formatters**
- JSON digest formatter
- Markdown report formatter
- German rating report (Jinja2 template)
- File output management

**4.3 Digest Repository**
- Implement DigestRepository
- Add digest versioning
- Create cluster tracking

**4.4 CLI Enhancements**
- Implement `newsanalysis export` command
- Add `newsanalysis stats` command
- Improve progress reporting

**4.5 Complete Testing**
- End-to-end test: full pipeline + digest
- Validate German report output
- Test incremental digest updates

### Success Criteria
- [ ] Daily digest generated successfully
- [ ] Deduplication removes duplicate stories
- [ ] German report matches quality standards
- [ ] Incremental updates work correctly
- [ ] Output files created in correct locations

### Estimated Effort
30-40 hours (1 week full-time)

---

## Phase 5: Optimization (Week 5)

### Goals
- Implement caching layer
- Optimize performance
- Add cost monitoring dashboard
- Reduce API costs to target

### Deliverables

**5.1 Caching Implementation**
- Exact match cache for classifications
- URL deduplication cache
- Summary content fingerprinting
- Cache hit rate monitoring

**5.2 Batch Processing Optimization**
- Optimize batch sizes
- Parallelize independent operations
- Reduce database query count
- Add connection pooling

**5.3 Cost Monitoring Dashboard**
- Implement `newsanalysis cost-report` command
- Add daily/weekly/monthly cost breakdowns
- Create budget alerts
- Generate cost optimization recommendations

**5.4 Performance Optimization**
- Profile slow operations
- Optimize database queries
- Add strategic indexes
- Reduce memory usage

**5.5 Advanced Features (Optional)**
- Semantic caching with embeddings
- Embedding-based pre-filtering
- Advanced prompt optimization

### Success Criteria
- [ ] Cache hit rate >70%
- [ ] Total monthly cost <$50
- [ ] Pipeline execution <3 minutes for daily run
- [ ] Cost dashboard shows accurate data
- [ ] Zero memory leaks

### Estimated Effort
30-50 hours (1 week full-time)

---

## Phase 6: Production Readiness (Week 6)

### Goals
- Complete test coverage
- Set up deployment automation
- Implement monitoring and logging
- Create documentation
- Production deployment

### Deliverables

**6.1 Testing Completion**
- Achieve >80% code coverage
- Add integration tests for all modules
- Create golden dataset (50 articles)
- Add performance regression tests

**6.2 Deployment Automation**
- Create deployment scripts
- Set up systemd service (Linux)
- Configure scheduled execution (cron)
- Write deployment documentation

**6.3 Monitoring & Logging**
- Implement health check command
- Add structured logging
- Configure log rotation
- Set up alert notifications

**6.4 Backup & Maintenance**
- Implement automated database backups
- Create vacuum/maintenance scripts
- Add data retention cleanup
- Document recovery procedures

**6.5 Documentation**
- Complete README.md
- Create user guide
- Document operational procedures
- Add troubleshooting guide

**6.6 Production Deployment**
- Deploy to production environment
- Configure monitoring
- Set up automated backups
- Perform smoke tests

### Success Criteria
- [ ] All tests pass in CI/CD
- [ ] Code coverage >80%
- [ ] Production deployment successful
- [ ] Automated backups working
- [ ] Monitoring alerts configured
- [ ] Documentation complete

### Estimated Effort
30-40 hours (1 week full-time)

---

## Risk Mitigation

### Technical Risks

**Risk**: OpenAI API costs exceed budget
- **Mitigation**: Implement cost tracking from Phase 2, add budget alerts
- **Contingency**: Reduce article volume, optimize prompts, use smaller models

**Risk**: Content extraction success rate <90%
- **Mitigation**: Test with real Swiss news sites early, implement Playwright fallback
- **Contingency**: Add more fallback methods, whitelist known-good sources

**Risk**: Performance too slow for production
- **Mitigation**: Performance testing in Phase 5, early optimization
- **Contingency**: Reduce concurrent operations, add caching, optimize queries

**Risk**: Database grows too large
- **Mitigation**: Implement retention policies from Phase 1
- **Contingency**: Migrate to PostgreSQL, add data archival

### Schedule Risks

**Risk**: Development takes longer than estimated
- **Mitigation**: Vertical slicing allows delivering partial functionality
- **Contingency**: Defer Phase 5 (optimization) or Phase 6 enhancements

**Risk**: External dependencies unavailable (OpenAI API downtime)
- **Mitigation**: Retry logic, circuit breakers, graceful degradation
- **Contingency**: Queue work for retry when API available

## Definition of Done (Per Phase)

Each phase is considered complete when:
1. All deliverables implemented
2. Unit tests written and passing
3. Integration tests passing (where applicable)
4. Code reviewed (self-review minimum)
5. Documentation updated
6. Success criteria met

## Deployment Strategy

### Development → Testing → Production

**Development**:
- Local environment
- Frequent iterations
- Mock OpenAI responses
- Small test datasets

**Testing/Staging**:
- Production-like environment
- Real OpenAI API (limited calls)
- Subset of production feeds
- End-to-end validation

**Production**:
- Full feed configuration
- Automated scheduling
- Monitoring and alerts
- Regular backups

## Post-Implementation

### Month 1-2: Monitoring & Optimization
- Monitor costs daily
- Track classification accuracy
- Optimize based on real usage
- Fix bugs and issues

### Month 3-6: Enhancements
- Add requested features
- Improve German language quality
- Expand news sources
- Advanced analytics

### Month 6+: Scale
- Migrate to PostgreSQL (if needed)
- Add web interface
- Multi-user support
- Custom ML models

## Conclusion

This phased approach ensures:
- **Working software** delivered incrementally
- **Risk mitigation** through early testing
- **Cost control** through monitoring from day one
- **Quality assurance** through continuous testing
- **Flexibility** to adjust based on learnings

**Total Estimated Effort**: 170-290 hours (6 weeks full-time)

**Critical Path**: Phases 1-4 (core functionality)
**Optional**: Phase 5-6 enhancements can be done incrementally

**Recommendation**: Start with Phase 1, validate learnings, adjust plan as needed.
