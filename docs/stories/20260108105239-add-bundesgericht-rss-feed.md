# Add Bundesgericht Published Decisions RSS Feed

## Summary

Added Federal Supreme Court (Bundesgericht) RSS feed for published decisions to Tier 1 Government Sources.

## Context / Problem

The news analysis system lacked coverage of Swiss Federal Supreme Court rulings. Initially the ATF feed (`atf_de.rss`) was considered, but investigation revealed it contains only historical landmark decisions with dates from 2007. The `aza_de_pub.rss` feed (10MB) contains recent published decisions with proper `pubDate` fields suitable for date filtering.

## What Changed

- Added new feed entry in `config/feeds.yaml` under Tier 1 Government Sources:
  - Name: "Bundesgericht Published Decisions"
  - URL: `http://relevancy.bger.ch/feeds/aza_de_pub.rss`
  - Priority: 1 (government source)
  - 7-day retention (`max_age_hours: 168`)

## How to Test

1. Verify feed is accessible:
   ```bash
   curl -s "http://relevancy.bger.ch/feeds/aza_de_pub.rss" | head -50
   ```

2. Run the collector and verify Bundesgericht items are fetched:
   ```bash
   newsanalysis run --collect-only
   ```

3. Check logs for successful parsing of Bundesgericht entries.

## Risk / Rollback Notes

- **Risk**: Feed uses HTTP (not HTTPS). Should work fine but may require attention if network policies block non-HTTPS.
- **Risk**: 10MB feed size is larger than typical news feeds. Monitor collection time.
- **Rollback**: Set `enabled: false` on the feed entry or remove the block entirely from `config/feeds.yaml`.
