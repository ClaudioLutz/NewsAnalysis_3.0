# Phase 1: Image Extraction Foundation Implementation

**Date:** 2026-01-09
**Story ID:** 20260109-phase1-image-extraction-foundation
**Phase:** Foundation (Week 1-2 of 4-phase rollout)

## Summary

Implemented the foundational infrastructure for extracting images from web articles, storing metadata in SQLite, and caching images in an organized filesystem structure. This is Phase 1 of a 4-phase implementation plan to add image extraction and email embedding capabilities to the news analysis pipeline.

## Context / Problem

The news analysis system generates daily email digests but lacks visual content. Articles often contain relevant images that would significantly improve the digest's readability and user engagement. Phase 1 establishes the database schema, extraction logic, and caching infrastructure needed before pipeline integration (Phase 2) and email embedding (Phase 3).

## What Changed

### Database Schema (Migration v3 → v4)

- **Added `article_images` table** with foreign key to `articles(id)`
  - Stores image metadata: URL, local path, dimensions, format, file size
  - Tracks extraction method (newspaper3k, beautifulsoup, og_image)
  - Marks featured/primary images with `is_featured` flag
  - Enforces uniqueness per article-image URL combination
- **Updated schema version** from 3 to 4 in `schema.sql` and `migrations.py`
- **Created migration function** `migrate_v3_to_v4()` with automatic table creation and indexing

**Files Modified:**
- [src/newsanalysis/database/schema.sql](../../../src/newsanalysis/database/schema.sql)
- [src/newsanalysis/database/migrations.py](../../../src/newsanalysis/database/migrations.py)

### Pydantic Models

- **Added `ArticleImage` model** in `article.py`
  - Metadata fields: image_url, local_path, dimensions, format, file_size
  - Extraction tracking: quality, method, is_featured
  - Timestamps for creation tracking
- **Updated `Article` model** with optional `images: List[ArticleImage]` field

**Files Modified:**
- [src/newsanalysis/core/article.py](../../../src/newsanalysis/core/article.py)

### Image Extraction Module

- **Created `ImageExtractor` class** in new `pipeline/extractors` package
  - Uses **newspaper3k** for featured image extraction (high quality)
  - Uses **BeautifulSoup** for additional images (medium quality)
  - Handles lazy-loaded images (data-src, data-lazy, data-original attributes)
  - Converts relative URLs to absolute using `urljoin`
  - Validates image URLs (scheme, extension whitelist)
  - Async HTML fetching with proper error handling
  - Configurable max images per article (default: 5)

**Files Created:**
- [src/newsanalysis/pipeline/extractors/__init__.py](../../../src/newsanalysis/pipeline/extractors/__init__.py)
- [src/newsanalysis/pipeline/extractors/image_extractor.py](../../../src/newsanalysis/pipeline/extractors/image_extractor.py)

### Filesystem Cache Manager

- **Created `ImageCache` class** for organized image storage
  - Year/month directory structure: `cache/images/YYYY/MM/`
  - Consistent filename generation: `article_{id}_{featured}_{hash}.ext`
  - URL hashing (MD5) for unique, reproducible filenames
  - Save/retrieve/delete operations with error handling
  - Cleanup routine for old images (configurable retention period)
  - Cache statistics: total images, size in MB, file count

**Files Created:**
- [src/newsanalysis/services/image_cache.py](../../../src/newsanalysis/services/image_cache.py)

### Dependencies

- **Added to pyproject.toml:**
  - `httpx>=0.27.0` - Async HTTP client for image downloads
  - `newspaper3k>=0.2.8` - Featured image extraction
  - `Pillow>=10.0.0` - Image processing (future phases)
- **Updated mypy overrides** to ignore `newspaper` type hints

**Files Modified:**
- [pyproject.toml](../../../pyproject.toml)

### Unit Tests

- **Created comprehensive test suite** with pytest
  - `test_image_extractor.py` - 12 test cases covering:
    - URL validation (valid/invalid schemes, extensions)
    - Dimension parsing (pixels, raw numbers, invalid inputs)
    - BeautifulSoup extraction (lazy loading, featured exclusion)
    - newspaper3k extraction (success/failure paths)
    - HTML fetching (success, non-HTML, timeout)
    - Full extraction workflow integration
  - `test_image_cache.py` - 15 test cases covering:
    - Path generation (structure, consistency, extensions)
    - Save/retrieve/delete operations
    - Old image cleanup (time-based retention)
    - Cache size calculation
    - Cache statistics
    - Empty directory cleanup

**Files Created:**
- [tests/unit/test_image_extractor.py](../../../tests/unit/test_image_extractor.py)
- [tests/unit/test_image_cache.py](../../../tests/unit/test_image_cache.py)

## How to Test

### Run Unit Tests

```bash
# Run all image-related tests
pytest tests/unit/test_image_extractor.py tests/unit/test_image_cache.py -v

# Run with coverage
pytest tests/unit/test_image_extractor.py tests/unit/test_image_cache.py --cov=newsanalysis.pipeline.extractors --cov=newsanalysis.services.image_cache
```

### Install Dependencies

```bash
# Install in development mode with all dependencies
pip install -e ".[dev]"

# Or install just the new dependencies
pip install httpx>=0.27.0 newspaper3k>=0.2.8 Pillow>=10.0.0
```

### Test Database Migration

```bash
# The migration will run automatically on next database connection
# To verify manually:
python -c "from newsanalysis.database.connection import get_connection; \
           from newsanalysis.database.migrations import run_migrations; \
           conn = get_connection(); \
           run_migrations(conn); \
           print('Migration successful')"
```

### Manual Image Extraction Test

```python
import asyncio
from newsanalysis.pipeline.extractors.image_extractor import ImageExtractor

async def test_extraction():
    extractor = ImageExtractor()
    images = await extractor.extract_images("https://www.nzz.ch/some-article")
    print(f"Extracted {len(images)} images")
    for img in images:
        print(f"  - {img.image_url} (featured={img.is_featured})")

asyncio.run(test_extraction())
```

### Test Image Cache

```python
from pathlib import Path
from newsanalysis.services.image_cache import ImageCache

# Create cache
cache = ImageCache(cache_root=Path("./test_cache"), days_to_keep=30)

# Generate path
path = cache.generate_image_path(
    article_id=123,
    image_url="https://example.com/image.jpg",
    is_featured=True
)
print(f"Generated path: {path}")

# Save test image
cache.save_image(path, b"fake image content")

# Get stats
stats = cache.get_cache_stats()
print(f"Cache stats: {stats}")
```

## Risk / Rollback Notes

### Risks

1. **Database Migration Risk**: Migration adds new table and updates schema version
   - **Likelihood**: Low
   - **Impact**: Medium (pipeline won't start if migration fails)
   - **Mitigation**: Migration is idempotent, uses IF NOT EXISTS checks

2. **newspaper3k Dependency**: External library may have compatibility issues
   - **Likelihood**: Low
   - **Impact**: Low (BeautifulSoup fallback available)
   - **Mitigation**: newspaper3k extraction is optional; BeautifulSoup works independently

3. **Disk Space**: Image cache could grow unbounded
   - **Likelihood**: Medium
   - **Impact**: Medium (disk space exhaustion)
   - **Mitigation**: Configurable retention period (default 30 days), cleanup routine available

### Rollback Plan

If critical issues arise:

1. **Database Rollback** (not recommended, data loss):
   ```sql
   DROP TABLE IF EXISTS article_images;
   UPDATE schema_info SET version = 3 WHERE version = 4;
   ```

2. **Disable Image Extraction**: Simply don't integrate into pipeline (Phase 2 integration not yet implemented)

3. **Dependency Rollback**:
   ```bash
   pip uninstall newspaper3k httpx
   # System will continue working without image extraction
   ```

### Known Limitations

- **Phase 1 only**: Image extraction is not yet integrated into the pipeline orchestrator
- **No async downloads**: Full async download with retry logic is planned for Phase 2
- **No CID embedding**: Email embedding implementation is Phase 3
- **No circuit breaker**: Resilience patterns are planned for Phase 4

## Next Steps

### Phase 2: Pipeline Integration (Week 3-4)

- Integrate ImageExtractor into scraping pipeline stage
- Implement async image downloads with aiohttp
- Add retry logic with Tenacity library
- Create integration tests for full pipeline

### Phase 3: Email Embedding (Week 5-6)

- Implement CID embedding for Outlook COM
- Update Jinja2 email template with image display
- Add graceful degradation (digest without images fallback)
- End-to-end tests with real email sending

### Phase 4: Production Hardening (Week 7-8)

- Add circuit breaker patterns (pybreaker)
- Implement cleanup routines and monitoring
- Comprehensive logging and metrics
- Performance optimization and load testing

## References

- [Technical Research Document](../../planning-artefacts/research/technical-image-extraction-email-embedding-research-20260109.md) - Comprehensive research on implementation approaches
- [Migration System Documentation](../../../src/newsanalysis/database/migrations.py) - Schema versioning and migrations
- [pytest Configuration](../../../pyproject.toml#L113-L124) - Test execution settings

## Change Type

- [x] New Feature
- [ ] Enhancement
- [ ] Bug Fix
- [ ] Refactoring
- [x] Database Schema Change
- [x] Dependency Update
- [ ] Performance Improvement
- [ ] Security Fix

## Impact Assessment

- **Pipeline**: No impact (not yet integrated)
- **Database**: Schema version upgrade from 3 to 4
- **Performance**: No impact (extraction not active)
- **Testing**: +27 new unit tests
- **Dependencies**: +3 new packages (httpx, newspaper3k, Pillow)
- **Security**: Image URL validation prevents malicious content

---

**Story Status**: ✅ Completed
**Tests Status**: ✅ Passing
**Migration Status**: ✅ Ready
**Documentation Status**: ✅ Complete
