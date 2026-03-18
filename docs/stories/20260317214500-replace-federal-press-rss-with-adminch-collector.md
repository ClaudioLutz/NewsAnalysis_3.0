## Summary

Replace the broken Federal Press Releases RSS feed with a new `adminch` collector type that scrapes the server-side-rendered news listing at `news.admin.ch/de/newnsb`. Only today's articles are collected.

## Context / Problem

The Swiss Federal Administration replaced their RSS feed (`/NSBSubscriber/feeds/rss`) with a Nuxt.js SPA in April 2025. The old endpoint returns HTTP 404 since mid-March 2026. The new platform has no RSS feed — only an email subscription service (`abo.news.admin.ch`). However, the news listing page is server-side rendered and contains structured article cards with date, title, description, and link (no images).

## What Changed

- **New collector**: `src/newsanalysis/pipeline/collectors/adminch.py` — `AdminChCollector` that:
  - Fetches the SSR HTML from `news.admin.ch/de/newnsb?newsCategoryIDs=medienmitteilung&sort=dateDecreasing&display=list`
  - Parses German dates (`17. März 2026`) from `<span class="meta-info__item">`
  - Extracts titles from `<h2>` elements and links from `/de/newnsb/{id}` hrefs
  - Filters to **today's articles only** (no stale content)
- **Updated collector factory**: `src/newsanalysis/pipeline/collectors/__init__.py` — added `"adminch"` type mapping
- **Updated config model**: `src/newsanalysis/core/config.py` — added `"adminch"` to `FeedConfig.type` literal
- **Updated feed config**: `config/feeds.yaml` — changed Federal Press Releases from `type: rss` to `type: adminch` with new URL

## How to Test

```bash
# Run unit tests
pytest tests/ -x -q

# Test the collector directly
python -c "
import asyncio
from newsanalysis.core.config import FeedConfig
from newsanalysis.pipeline.collectors import create_collector

async def test():
    config = FeedConfig(name='Federal Press Releases', type='adminch',
        url='https://www.news.admin.ch/de/newnsb', priority=1,
        max_age_hours=24, rate_limit_seconds=5.0)
    articles = await create_collector(config).collect()
    print(f'{len(articles)} articles collected')
    for a in articles:
        print(f'  {a.title} ({a.published_at})')

asyncio.run(test())
"

# Full pipeline test
python -m newsanalysis.cli.main run --limit 5
```

## Risk / Rollback Notes

- **Low risk**: The old RSS feed was already returning 404. This restores functionality that was lost.
- **Fragile selectors**: The collector relies on CSS classes (`card--list-without-image`, `meta-info__item`) and HTML structure that could change if the federal government updates their website. Monitor logs for `adminch_collection_failed` events.
- **Rollback**: Set `enabled: false` in `config/feeds.yaml` for the Federal Press Releases feed.
