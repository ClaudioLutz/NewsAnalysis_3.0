# Swiss credit risk intelligence RSS feed integration specifications

Nine Swiss news sources were researched for credit risk pipeline integration. **Seven sources offer active RSS feeds** with documented URLs, while the Swiss Bankers Association has discontinued RSS in favor of newsletters and the Bundesgericht's exact feed URLs require manual subscription configuration. The SNB provides the most comprehensive feed bundle with **18+ specialized feeds** covering monetary policy, interest rates, and economic indicators.

## Swiss National Bank offers 18+ specialized feeds

The SNB maintains the most extensive RSS infrastructure among Swiss financial regulators, using **RSS 1.0 (RDF)** format across all feeds. The official documentation page at `snb.ch/en/services-events/digital-services/rss-calendar-feeds` lists feeds in four languages (de, en, fr, it).

**Priority 1 feeds for credit risk monitoring:**

| Feed | URL | Purpose |
|------|-----|---------|
| Monetary Policy | `https://www.snb.ch/public/en/rss/mopo` | Policy announcements, rate decisions |
| Interest Rates | `https://www.snb.ch/public/en/rss/interestRates` | Current rate updates |
| Ad Hoc Announcements | `https://www.snb.ch/public/en/rss/adhoc` | Market-moving disclosures (Art. 53 LR) |
| Press Releases | `https://www.snb.ch/public/en/rss/pressrel` | General press releases |
| Exchange Rates | `https://www.snb.ch/public/en/rss/exchangeRates` | Currency data |
| Statistical Publications | `https://www.snb.ch/public/en/rss/statistics` | Economic indicators |

**Additional SNB feeds available:** Speeches (`/speeches`), Quarterly Bulletin (`/quartbul`), Working Papers (`/papers`), Business Cycle Signals (`/buscycletrends`), SNB Bills (`/snbbbills`), Federal Bonds (`/bund`), USD Auctions (`/usdauctions`), Repos (`/repos`), Annual Report (`/annrep`), Research Reports (`/researchreports`), Events (`/events`), Interviews (`/interviews`).

**URL pattern:** Replace `/en/` with `/de/`, `/fr/`, or `/it/` for other languages.

**Technical specifications:** No authentication required. Publicly accessible via standard HTTP requests. No documented rate limits. iCalendar feeds also available for event scheduling.

---

## FINMA provides two primary regulatory feeds

The Swiss Financial Market Authority offers RSS feeds at `finma.ch/en/rss/` covering news and sanctions. These are critical for regulatory compliance and enforcement action monitoring.

| Feed | URL | Content |
|------|-----|---------|
| News | `https://www.finma.ch/en/rss/news/` | All news, enforcement actions, press releases |
| Sanctions | `https://www.finma.ch/en/rss/sanktionen/` | International sanctions, FATF statements, asset freezes |

**Language variants:**
- German: `https://www.finma.ch/de/rss/news/` and `/de/rss/sanktionen/`
- French: `https://www.finma.ch/fr/rss/news/`
- Italian: `https://www.finma.ch/it/rss/news/`

**Warning list limitation:** The unauthorized operators warning list at `finma.ch/en/finma-public/warnungen/warning-list/` is web-only with no direct RSS. Consider periodic scraping or MyFINMA email subscription for this data.

**Priority:** 1 (regulatory authority)

---

## Federal Administration aggregates via news.admin.ch

The Swiss Federal Administration's press release system uses a centralized RSS infrastructure supporting departmental filtering.

| Feed | URL |
|------|-----|
| All Federal Press Releases | `https://www.news.admin.ch/NSBSubscriber/feeds/rss` |
| XML Messages Endpoint | `https://www.news.admin.ch/NSBSubscriber/messages` |

**Subscription customization:** The RSS subscription dashboard at `admin.ch/gov/de/start/dokumentation/medienmitteilungen/rss-feeds.html` allows filtering by department (SECO, WBF/EAER, EFD/FDF) and topic to generate custom feed URLs.

**SECO-specific feeds:** Access SECO press releases through the subscription interface or monitor their documentation at `seco.admin.ch/seco/en/home/Publikationen_Dienstleistungen/RSS_Feeds.html`.

**Technical notes:** RSS 2.0 format. ~40,000 historical press releases since 1997 in repository. Content in German, French, Italian. **Priority:** 1

---

## Bundesgericht feeds require subscription activation

The Swiss Federal Supreme Court provides RSS through its Eurospider-powered database, but exact feed URLs are **not publicly displayed** without user interaction.

**Official RSS subscription page:** `https://search.bger.ch/home/juridiction/feed-rss.html`

**Three feed categories documented:**
- **AZA Feed** — All decisions (unpublished since 2000, all since 2007)
- **BGE Feed** — Leading decisions/Leitentscheide (official collection since 1954)
- **EMRK Feed** — European Court of Human Rights decisions

**Relevant case prefixes for debt/bankruptcy:**
- `5A_xxx/yyyy` — Debt enforcement (SchKG), family law, civil matters
- `4A_xxx/yyyy` — Commercial law, contract disputes

**Alternative data sources:** The third-party service **bger-update.ch** provides daily automated decision updates (updated 13:00 daily) with categorical filtering. For bulk research, the Swiss Federal Supreme Court Dataset on Zenodo (DOI: 10.5281/zenodo.14867950) contains **127,477 cases** from 2007-2024 in CSV/Parquet formats.

**Priority:** 1 (judicial authority) | **Limitation:** Manual subscription required

---

## FintechNews.ch offers extensive WordPress feeds

FintechNews Switzerland provides a full WordPress RSS 2.0 implementation with category-specific feeds.

| Feed | URL |
|------|-----|
| **Main Feed** | `https://fintechnews.ch/feed/` |
| Blockchain/Bitcoin | `https://fintechnews.ch/blockchain_bitcoin/feed/` |
| AI/Fintech | `https://fintechnews.ch/aifintech/feed/` |
| Regtech | `https://fintechnews.ch/regtech/feed/` |
| Open Banking | `https://fintechnews.ch/open-banking/feed/` |
| Virtual Banking | `https://fintechnews.ch/virtual-banking/feed/` |
| Funding | `https://fintechnews.ch/funding/feed/` |
| Insurtech | `https://fintechnews.ch/insurtech/feed/` |
| P2P Lending | `https://fintechnews.ch/p2plending/feed/` |

**Technical specifications:** RSS 2.0 with Dublin Core extensions. **3-7 articles daily**. English primary language. 10-20 items retained in feed. Article excerpts with featured images included. Standard WordPress item structure with `<title>`, `<link>`, `<dc:creator>`, `<pubDate>`, `<category>`, `<description>`, `<content:encoded>`.

**Priority:** 2 (financial sector) | No authentication | No known rate limits

---

## Le Temps economy feed covers French-speaking Switzerland

**RSS directory:** `https://www.letemps.ch/rss`

| Feed | URL |
|------|-----|
| **Économie (Business)** | `https://www.letemps.ch/economie.rss` |
| All Articles | `https://www.letemps.ch/articles.rss` |
| Suisse | `https://www.letemps.ch/suisse.rss` |
| Monde | `https://www.letemps.ch/monde.rss` |
| Cyber | `https://www.letemps.ch/cyber.rss` |
| Carrières et Formation | `https://www.letemps.ch/carrieres-et-formation.rss` |
| Immobilier | `https://www.letemps.ch/immobilier.rss` |

**Technical specifications:** RSS 2.0. French language (fr). Excerpts in feed; full articles behind subscription paywall (CHF 1 first month promotional). Published by Le Temps SA, Geneva.

**Priority:** 3 (general news) | **URL pattern:** `letemps.ch/[section].rss`

---

## RSI economia feed covers Italian-speaking Switzerland

**RSS directory:** `https://www.rsi.ch/la-rsi/Feed-Rss--947722.html`

| Feed | URL |
|------|-----|
| **Economia** | `https://www.rsi.ch/info/economia/?f=rss` |
| Info (All News) | `https://www.rsi.ch/info/?f=rss` |
| Ticino/Grigioni | `https://www.rsi.ch/info/ticino-e-grigioni-e-insubria/?f=rss` |
| Svizzera | `https://www.rsi.ch/info/svizzera/?f=rss` |
| Mondo | `https://www.rsi.ch/info/mondo/?f=rss` |
| Consumi (Consumer) | `https://www.rsi.ch/info/consumi/?f=rss` |

**Technical specifications:** RSS/XML format. Italian language (it). Part of SRG SSR public broadcasting — **no paywall**. Query parameter pattern: `?f=rss`.

**Priority:** 3 (general news) | Public broadcaster = reliable access

---

## LaRegione provides Ticino regional coverage

**RSS directory:** `https://www.laregione.ch/rss`

| Feed | URL |
|------|-----|
| **Economia** | `https://media.laregione.ch/files/domains/laregione.ch/rss/rss_economia.xml` |
| Main Feed | `https://media.laregione.ch/files/domains/laregione.ch/rss/feed_rss.xml` |
| Ticino/Cantone | `https://media.laregione.ch/files/domains/laregione.ch/rss/rss_ticino.xml` |
| Top News | `https://media.laregione.ch/files/domains/laregione.ch/rss/rss_aperture.xml` |
| Svizzera | `https://media.laregione.ch/files/domains/laregione.ch/rss/rss_svizzera.xml` |
| Estero | `https://media.laregione.ch/files/domains/laregione.ch/rss/rss_estero.xml` |

**Technical specifications:** Static XML files on media subdomain. Italian language (it). Titles and subtitles in feed; full content behind subscription. Published by Regiopress SA, Bellinzona.

**Priority:** 3 (regional news) | Strong Ticino business coverage

---

## Swiss Bankers Association has no RSS feeds

**SwissBanking (swissbanking.ch) has discontinued RSS support.** The association now uses newsletter subscriptions and social media for distribution.

**Available alternatives:**
- **Insight Newsletter:** Subscribe at `swissbanking.ch/en/forms/subscription-insight-quarterly-newsletter`
- **News page (scraping candidate):** `swissbanking.ch/en/media-politics/news`
- **Publications:** `swissbanking.ch/en/media-politics/publications`

**Languages:** German, French, Italian, English available on website.

**Recommendation:** Implement web scraping for the news page or subscribe to the quarterly Insight newsletter and process via email parsing.

**Priority:** 2 (financial sector) | **Status:** ❌ No RSS

---

## Implementation priority matrix

| Priority | Source | Feed URL | Update Frequency |
|----------|--------|----------|------------------|
| **1** | SNB Monetary Policy | `snb.ch/public/en/rss/mopo` | Event-driven |
| **1** | SNB Interest Rates | `snb.ch/public/en/rss/interestRates` | Daily/intraday |
| **1** | FINMA News | `finma.ch/en/rss/news/` | Several/week |
| **1** | FINMA Sanctions | `finma.ch/en/rss/sanktionen/` | As announced |
| **1** | news.admin.ch | `news.admin.ch/NSBSubscriber/feeds/rss` | Multiple/day |
| **1** | Bundesgericht | Subscription at search.bger.ch | Daily |
| **2** | FintechNews.ch | `fintechnews.ch/feed/` | 3-7 articles/day |
| **2** | SwissBanking | ❌ Newsletter only | Quarterly |
| **3** | Le Temps Économie | `letemps.ch/economie.rss` | Multiple/day |
| **3** | RSI Economia | `rsi.ch/info/economia/?f=rss` | Multiple/day |
| **3** | LaRegione Economia | `media.laregione.ch/.../rss_economia.xml` | Daily |

---

## Technical integration notes

**Feed formats:** SNB uses RSS 1.0 (RDF); all others use RSS 2.0 or standard XML.

**Authentication:** All feeds are publicly accessible without authentication except Bundesgericht (requires subscription configuration).

**Rate limiting:** No documented limits on any source. Standard HTTP request etiquette recommended (respect robots.txt, implement reasonable polling intervals of 15-60 minutes for most feeds, 5 minutes for real-time SNB rate feeds).

**Multilingual strategy:** SNB, FINMA, and news.admin.ch offer identical content in 4 languages. For credit risk intelligence, German feeds typically publish first for government sources.

**Paywall considerations:** Le Temps and LaRegione RSS provide excerpts only. RSI is public broadcasting with full access. FintechNews provides full article content in feeds.