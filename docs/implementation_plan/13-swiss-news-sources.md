# Swiss News Sources Reference

## Overview

This document provides the complete catalog of Swiss news sources used in the NewsAnalysis POC, with exact URLs, integration methods, and implementation notes. All sources are optimized for Swiss business and financial news relevant to Creditreform's credit risk analysis.

## Source Tiers (Priority Levels)

### Tier 1: Government & Regulatory (Priority 1)
**Retention**: 7 days
**Rate Limit**: 5 seconds between requests
**Rationale**: Regulatory changes have long-term credit risk implications

### Tier 2: Financial & Business (Priority 2)
**Retention**: 3 days
**Rate Limit**: 3 seconds between requests
**Rationale**: Financial news is relevant for quarterly analysis

### Tier 3: General News (Priority 3)
**Retention**: 1 day
**Rate Limit**: 2 seconds between requests
**Rationale**: General news becomes stale quickly, filter aggressively

---

## RSS Feed Sources

### Tier 1: Government & Regulatory

#### FINMA (Swiss Financial Market Supervisory Authority)
```yaml
finma_news:
  type: rss
  urls:
    - "https://www.finma.ch/en/rss/news/"
  priority: 1
  max_age_hours: 168  # 7 days
  language: en
  notes: |
    Official regulatory announcements from FINMA.
    Critical for compliance and regulatory risk assessment.
```

#### FINMA Sanctions
```yaml
finma_sanctions:
  type: rss
  urls:
    - "https://www.finma.ch/en/rss/sanktionen/"
  priority: 1
  max_age_hours: 168
  language: en
  notes: |
    Enforcement actions and sanctions.
    High-value for credit risk signals.
```

### Tier 2: Financial & Business News

#### Handelszeitung (Business Weekly)
```yaml
handelszeitung:
  type: rss
  urls:
    - "https://www.handelszeitung.ch/rss.xml"
  priority: 2
  max_age_hours: 72  # 3 days
  language: de
  notes: |
    Leading Swiss business publication.
    Good coverage of bankruptcies and financial distress.
```

#### Finews (Financial News)
```yaml
finews:
  type: rss
  urls:
    - "https://www.finews.ch/rss"
  priority: 2
  max_age_hours: 72
  language: de
  notes: |
    Specialized financial news portal.
    Focus on banking, fintech, wealth management.
```

#### Cash.ch (Financial Portal)
```yaml
cash:
  type: rss
  urls:
    - "https://www.cash.ch/rss"
  priority: 2
  max_age_hours: 72
  language: de
  notes: |
    Financial news and market data.
    Good coverage of listed companies.
```

#### Finanzen.ch (Finance Portal)
```yaml
finanzen_ch:
  type: rss
  urls:
    - "https://www.finanzen.ch/rss/news"
    - "https://www.finanzen.ch/rss/analysen"
  priority: 2
  max_age_hours: 72
  language: de
  notes: |
    Financial news and analysis.
    Two feeds: news and analysis/opinion.
```

#### Startupticker (Startup News)
```yaml
startupticker:
  type: rss
  urls:
    - "https://www.startupticker.ch/feed/"
  priority: 2
  max_age_hours: 72
  language: de
  notes: |
    Swiss startup ecosystem news.
    Relevant for KMU financing and venture risk.
```

#### FinTech News Switzerland
```yaml
fintechnews_ch:
  type: rss
  urls:
    - "https://fintechnews.ch/feed/"
  priority: 2
  max_age_hours: 72
  language: en
  notes: |
    FinTech industry news for Switzerland.
    Regulatory and innovation coverage.
```

### Tier 3: General News

#### NZZ (Neue Zürcher Zeitung)
```yaml
nzz:
  type: rss
  urls:
    - "https://www.nzz.ch/recent.rss"      # Recent articles
    - "https://www.nzz.ch/wirtschaft.rss"  # Business section
    - "https://www.nzz.ch/schweiz.rss"     # Switzerland section
  priority: 3
  max_age_hours: 24
  language: de
  notes: |
    Switzerland's newspaper of record.
    High quality journalism, three feeds for comprehensive coverage.
    Known-good RSS implementation.
```

#### Tages-Anzeiger (Tamedia)
```yaml
tages_anzeiger:
  type: rss
  urls:
    - "https://partner-feeds.publishing.tamedia.ch/rss/tagesanzeiger/front"
    - "https://partner-feeds.publishing.tamedia.ch/rss/tagesanzeiger/schweiz"
    - "https://partner-feeds.publishing.tamedia.ch/rss/tagesanzeiger/ticker"
  priority: 3
  max_age_hours: 24
  language: de
  notes: |
    Major Zurich daily newspaper.
    Use official Tamedia partner feeds (avoid malformed *.ch/rss).
    Three feeds: front page, Switzerland, and ticker (breaking news).
```

#### Der Bund (Tamedia - Bern)
```yaml
der_bund:
  type: rss
  urls:
    - "https://partner-feeds.publishing.tamedia.ch/rss/derbund/"
    - "https://partner-feeds.publishing.tamedia.ch/rss/derbund/schweiz"
    - "https://partner-feeds.publishing.tamedia.ch/rss/derbund/wirtschaft"
    - "https://partner-feeds.publishing.tamedia.ch/rss/derbund/ticker"
  priority: 3
  max_age_hours: 24
  language: de
  notes: |
    Bern regional newspaper (Tamedia).
    Use official partner feeds.
    Four feeds: main, Switzerland, business, ticker.
```

#### Tribune de Genève (Tamedia - Romandie)
```yaml
tribune_de_geneve:
  type: rss
  urls:
    - "https://partner-feeds.publishing.tamedia.ch/rss/tdg/front"
  priority: 3
  max_age_hours: 24
  language: fr
  notes: |
    Geneva newspaper (French-speaking Switzerland).
    Romandie regional coverage.
```

#### 24 heures (Tamedia - Romandie)
```yaml
24heures:
  type: rss
  urls:
    - "https://partner-feeds.publishing.tamedia.ch/rss/24heures/front"
  priority: 3
  max_age_hours: 24
  language: fr
  notes: |
    Lausanne/Vaud newspaper (French-speaking).
    Romandie business coverage.
```

#### SRF (Swiss Public Broadcasting - German)
```yaml
srf_news:
  type: rss
  urls:
    - "https://www.srf.ch/news/bnf/rss/1646"  # Das Neueste (Latest)
    - "https://www.srf.ch/news/bnf/rss/1890"  # Schweiz (Switzerland)
    - "https://www.srf.ch/news/bnf/rss/1926"  # Wirtschaft (Business)
  priority: 3
  max_age_hours: 24
  language: de
  notes: |
    Swiss public broadcaster (German).
    BNF feeds with stable numeric IDs.
    Three feeds: latest, Switzerland, business.
```

#### Swissinfo (International Perspective)
```yaml
swissinfo:
  type: rss
  urls:
    - "https://cdn.prod.swi-services.ch/rss/de/rssxml/latest-news/rss"
  priority: 3
  max_age_hours: 24
  language: de
  notes: |
    Swiss international news service (multilingual).
    Good for Swiss news with international impact.
```

---

## HTML Parsing Sources

### BusinessClass Ost (Eastern Switzerland Business)
```yaml
businessclassost:
  type: html
  url: "https://www.businessclassost.ch/news-categories/news"
  priority: 2
  max_age_hours: 72
  language: de

  selectors:
    item: "div.card.w-dyn-item"           # Article container
    date: "div.datum"                      # Publication date
    title: "h2.heading.h4"                 # Article title
    hidden_url: "div.hiddenarticleurl"     # URL (non-standard location)

  notes: |
    Regional business news for Eastern Switzerland.
    No RSS feed - requires HTML parsing with custom selectors.
    URL is stored in hidden div (unusual pattern).
    Relevant for KMU and regional business news.
```

**Implementation Notes**:
```python
# BeautifulSoup implementation
soup = BeautifulSoup(html, 'html.parser')

items = []
for card in soup.select('div.card.w-dyn-item'):
    date_elem = card.select_one('div.datum')
    title_elem = card.select_one('h2.heading.h4')
    url_elem = card.select_one('div.hiddenarticleurl')

    if date_elem and title_elem and url_elem:
        items.append({
            'date': date_elem.text.strip(),
            'title': title_elem.text.strip(),
            'url': url_elem.text.strip()
        })
```

---

## Sitemap Sources (Currently Disabled)

### 20 Minuten (High Volume)
```yaml
20min:
  type: sitemap
  url: "https://www.20min.ch/sitemaps/de/news.xml"
  priority: 3
  max_age_hours: 24
  language: de

  notes: |
    Major tabloid-style news portal.
    CURRENTLY DISABLED: High volume, lower quality for credit risk.
    Sitemap format: <url><loc>, <news:title>, <news:publication_date>

    Enable only if broader news coverage needed.
    Expect 100+ articles per day.
```

### Nau.ch
```yaml
nau:
  type: sitemap
  url: "https://www.nau.ch/_sitemap"
  priority: 3
  max_age_hours: 24
  language: de

  notes: |
    CURRENTLY DISABLED: Sitemap index (requires parsing sub-sitemaps).
    Complex multi-level structure.
    Lower priority for credit risk analysis.
```

---

## Disabled Sources

### Google News RSS (DISABLED - Technical Issues)
```yaml
# DISABLED: Causes redirect loop errors
google_news_rss:
  wirtschaft: "https://news.google.com/rss/search?q=wirtschaft&hl=de-CH&gl=CH&ceid=CH:de"
  fintech: "https://news.google.com/rss/search?q=fintech&hl=de-CH&gl=CH&ceid=CH:de"
  schweiz: "https://news.google.com/rss/search?q=Schweiz&hl=de-CH&gl=CH&ceid=CH:de"

  issue: |
    Google News uses redirect URLs that cause infinite loops.
    Example: https://news.google.com/rss/articles/CBMi...

    Requires Google News URL decoder to extract real article URLs.
    Disabled in POC due to complexity and reliability issues.

  potential_fix: |
    Use Google News API (paid) or implement robust redirect handler.
    Or rely on direct RSS feeds from quality sources (current approach).
```

### Watson (Optional - Currently Disabled)
```yaml
watson:
  type: rss
  url: "https://www.watson.ch/api/1.0/rss.xml"
  priority: 3
  language: de

  notes: |
    Popular Swiss news platform.
    DISABLED: More entertainment/lifestyle than business.
    Enable if broader coverage needed.
```

### Blick (Optional - Currently Disabled)
```yaml
blick:
  type: rss
  url: "https://www.blick.ch/rss.xml"
  priority: 3
  language: de

  notes: |
    Major tabloid newspaper.
    DISABLED: Lower quality for credit risk analysis.
    Enable if broader coverage needed.
```

### RTS Info (French - Currently Disabled)
```yaml
rts_info:
  type: rss
  url: "https://www.rts.ch/info/?flux=rss"
  priority: 3
  language: fr

  notes: |
    Swiss public broadcaster (French).
    DISABLED: Romandie coverage already via Tribune/24heures.
    Enable if French-language coverage priority increases.
```

### Ticinonline (Italian - Currently Disabled)
```yaml
tio:
  type: rss
  urls:
    - "https://media.tio.ch/files/domains/tio.ch/rss/feed_rss.xml"
    - "https://media.tio.ch/files/domains/tio.ch/rss/rss_ticino.xml"
  priority: 3
  language: it

  notes: |
    Ticino news (Italian-speaking Switzerland).
    DISABLED: Previous certificate issues on main domain.
    Use media.tio.ch feeds if enabling.
```

---

## Integration Patterns

### RSS Feed Integration

**Standard Pattern**:
```python
import feedparser

def collect_rss(feed_url: str, max_age_hours: int = 24) -> List[Article]:
    """Collect articles from RSS feed."""

    # Parse feed
    feed = feedparser.parse(
        feed_url,
        agent="NewsAnalysis/2.0 (creditreform.ch)",
        request_headers={
            "Accept-Language": "de-CH, de, en",
            "Accept-Encoding": "gzip, deflate"  # NOT zstd!
        }
    )

    # Handle malformed feeds
    if feed.bozo and not feed.entries:
        raise FeedParseError(f"Failed to parse: {feed.bozo_exception}")

    # Extract articles
    articles = []
    cutoff = datetime.now() - timedelta(hours=max_age_hours)

    for entry in feed.entries:
        published = parse_date(entry.get('published'))

        if published and published > cutoff:
            articles.append(Article(
                url=entry.get('link'),
                title=entry.get('title'),
                published_at=published,
                source=get_source_name(feed_url)
            ))

    return articles
```

### Sitemap Integration

**XML Parsing Pattern**:
```python
from lxml import etree

def collect_sitemap(sitemap_url: str) -> List[Article]:
    """Collect articles from news sitemap."""

    response = requests.get(sitemap_url)
    root = etree.fromstring(response.content)

    # Namespaces
    ns = {
        'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
        'news': 'http://www.google.com/schemas/sitemap-news/0.9'
    }

    articles = []
    for url_elem in root.xpath('//sitemap:url', namespaces=ns):
        loc = url_elem.xpath('sitemap:loc/text()', namespaces=ns)[0]

        # Extract news-specific fields
        news = url_elem.xpath('news:news', namespaces=ns)
        if news:
            title = news[0].xpath('news:title/text()', namespaces=ns)[0]
            pub_date = news[0].xpath('news:publication_date/text()', namespaces=ns)[0]

            articles.append(Article(
                url=loc,
                title=title,
                published_at=parse_date(pub_date)
            ))

    return articles
```

### HTML Parsing Pattern

**BeautifulSoup Pattern**:
```python
def collect_html(config: HTMLSourceConfig) -> List[Article]:
    """Collect articles from HTML page."""

    response = requests.get(config.url)
    soup = BeautifulSoup(response.text, 'html.parser')

    articles = []
    for item in soup.select(config.selectors['item']):
        # Extract fields using configured selectors
        date_elem = item.select_one(config.selectors['date'])
        title_elem = item.select_one(config.selectors['title'])
        url_elem = item.select_one(config.selectors['hidden_url'])

        if date_elem and title_elem and url_elem:
            articles.append(Article(
                url=url_elem.text.strip(),
                title=title_elem.text.strip(),
                published_at=parse_date(date_elem.text.strip()),
                source=config.name
            ))

    return articles
```

---

## Source Statistics (from POC)

### Volume Estimates

**Daily Article Volumes** (estimated):
```
Tier 1 (Government):          5-10 articles/day
Tier 2 (Financial):          20-30 articles/day
Tier 3 (General News):       80-120 articles/day
───────────────────────────────────────────────
Total collected:            105-160 articles/day
After filtering (15%):       15-25 articles/day
```

### Success Rates

**RSS Feed Reliability**:
- NZZ: 99% uptime
- Tamedia feeds: 98% uptime
- SRF: 99% uptime
- FINMA: 100% uptime (critical)
- Handelszeitung: 95% uptime

**Content Extraction Success**:
- Trafilatura success: 70-85%
- Playwright fallback: 95%
- Combined: 90%+ success rate

---

## Language Distribution

**German (de)**: ~85% of sources
- Primary language for Swiss business

**French (fr)**: ~10% of sources
- Romandie coverage (Geneva, Lausanne)

**English (en)**: ~5% of sources
- FINMA, Swissinfo, FinTech News

**Italian (it)**: Currently disabled
- Would add Ticino coverage if enabled

---

## Recommended Starting Configuration

### Minimal MVP (6 sources)
```yaml
feeds:
  # Tier 1: Government
  - finma_news

  # Tier 2: Financial
  - handelszeitung
  - finews

  # Tier 3: General
  - nzz
  - tages_anzeiger
  - srf_news
```

**Volume**: ~50 articles/day → 5-8 after filtering

### Balanced Production (12 sources)
```yaml
feeds:
  # Tier 1: Government
  - finma_news
  - finma_sanctions

  # Tier 2: Financial
  - handelszeitung
  - finews
  - cash
  - finanzen_ch
  - businessclassost

  # Tier 3: General
  - nzz (3 feeds)
  - tages_anzeiger (3 feeds)
  - der_bund (4 feeds)
  - srf_news (3 feeds)
  - swissinfo
```

**Volume**: ~120 articles/day → 15-20 after filtering

### Maximum Coverage (18 sources)
All of the above plus:
```yaml
  - tribune_de_geneve
  - 24heures
  - startupticker
  - fintechnews_ch
```

**Volume**: ~150 articles/day → 20-25 after filtering

---

## Implementation Checklist

**Per Source**:
- [ ] Verify RSS/sitemap URL is accessible
- [ ] Test feed parsing (handle bozo feeds)
- [ ] Validate date parsing (multiple formats)
- [ ] Configure rate limiting (respect robots.txt)
- [ ] Test content extraction success rate
- [ ] Add to feeds.yaml with correct priority
- [ ] Monitor for feed changes/deprecation

**Operational**:
- [ ] Set up feed health monitoring
- [ ] Alert on feed failures (>24h down)
- [ ] Track per-source article counts
- [ ] Monitor extraction success rates
- [ ] Regular review of source value (quarterly)

---

## Source Maintenance

### Known Issues

**Tamedia Feeds**:
- Use partner-feeds.publishing.tamedia.ch (not direct *.ch/rss)
- Direct feeds are often malformed
- Partner feeds are stable and well-maintained

**Google News**:
- Redirect URLs require decoding
- Disabled until robust handler implemented
- Alternative: Use direct source RSS feeds

**ZSTD Compression**:
- Some Swiss sites use Zstandard compression
- Not supported by default Python requests
- Solution: Use Accept-Encoding: gzip, deflate (not zstd)

### Adding New Sources

1. **Identify feed URL** (RSS, sitemap, or HTML)
2. **Test in browser** (validate XML/HTML structure)
3. **Determine priority tier** (1, 2, or 3)
4. **Configure selectors** (if HTML source)
5. **Add to feeds.yaml**
6. **Test collection** (newsanalysis run --limit 5)
7. **Monitor quality** (first week)
8. **Adjust retention** (based on value)

---

## Next Steps

- Review [07-configuration-management.md](07-configuration-management.md) for feeds.yaml structure
- Review [03-modular-pipeline-design.md](03-modular-pipeline-design.md) for collector implementation
- Implement RSS/sitemap/HTML collectors per source type
- Configure feed priorities and retention policies
