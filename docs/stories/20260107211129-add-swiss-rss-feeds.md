# Add Swiss RSS Feeds from Research

## Summary

Added 10 new RSS feeds to `config/feeds.yaml` based on research in `docs/planning-artefacts/research/research-rss-feeds.md`. Expands coverage to include SNB (Swiss National Bank), Federal Administration press releases, and Italian-language sources.

## Context / Problem

The existing feeds.yaml lacked coverage for key Swiss government sources (SNB, Federal Administration) and Italian-language regional sources (Ticino). Research identified 7 sources with active RSS feeds suitable for credit risk intelligence.

## What Changed

**Tier 1 - Government Sources (7 feeds added):**
- SNB Monetary Policy (`snb.ch/public/de/rss/mopo`)
- SNB Interest Rates (`snb.ch/public/de/rss/interestRates`)
- SNB Ad Hoc Announcements (`snb.ch/public/de/rss/adhoc`)
- SNB Press Releases (`snb.ch/public/de/rss/pressrel`)
- SNB Statistics (`snb.ch/public/de/rss/statistics`)
- SNB Business Cycle (`snb.ch/public/de/rss/buscycletrends`)
- Federal Press Releases (`news.admin.ch/NSBSubscriber/feeds/rss`)

**Tier 3 - Regional Sources (3 feeds added):**
- Le Temps Économie (French, Romandie)
- RSI Economia (Italian, Ticino)
- LaRegione Economia (Italian, Ticino)

**Files modified:**
- `config/feeds.yaml`

## How to Test

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/feeds.yaml'))"

# Test feed fetching (if newsanalysis CLI available)
newsanalysis run --dry-run
```

## Risk / Rollback Notes

- **Risk:** New feeds may have different RSS formats (SNB uses RSS 1.0/RDF). Monitor for parsing errors.
- **Risk:** Federal press releases feed may have high volume. Consider filtering by department if noise is excessive.
- **Rollback:** Revert changes to `config/feeds.yaml` or set `enabled: false` on individual feeds.
