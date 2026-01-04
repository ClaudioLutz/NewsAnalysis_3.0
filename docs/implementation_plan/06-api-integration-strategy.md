# API Integration Strategy

## Overview

The NewsAnalysis system integrates with multiple external APIs and services: OpenAI for AI processing, news sources (RSS/HTTP), and optional caching services. This document outlines integration patterns, error handling, rate limiting, and cost optimization strategies.

## OpenAI API Integration

### Client Configuration

```python
from openai import AsyncOpenAI
from typing import Optional
import asyncio

class OpenAIClient:
    def __init__(
        self,
        api_key: str,
        default_model: str = "gpt-4o-mini",
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries
        )
        self.default_model = default_model

    async def complete(
        self,
        messages: list,
        model: Optional[str] = None,
        temperature: float = 0.0,
        response_format: dict = {"type": "json_object"}
    ) -> str:
        """Call OpenAI API with automatic retry and error handling."""

        try:
            response = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                temperature=temperature,
                response_format=response_format
            )

            return response.choices[0].message.content

        except Exception as e:
            # Handle errors (see error handling section)
            raise
```

### Batch API for Cost Savings (50% Discount)

```python
async def create_batch_job(
    self,
    requests: List[Dict],
    endpoint: str = "/v1/chat/completions",
    completion_window: str = "24h"
) -> str:
    """Create batch job with OpenAI Batch API."""

    # Upload requests file
    file_content = "\n".join(json.dumps(req) for req in requests)
    file = await self.client.files.create(
        file=file_content.encode(),
        purpose="batch"
    )

    # Create batch
    batch = await self.client.batches.create(
        input_file_id=file.id,
        endpoint=endpoint,
        completion_window=completion_window
    )

    return batch.id

async def wait_for_batch(self, batch_id: str, poll_interval: int = 60):
    """Wait for batch completion."""

    while True:
        batch = await self.client.batches.retrieve(batch_id)

        if batch.status == "completed":
            return await self.retrieve_batch_results(batch.output_file_id)
        elif batch.status in ["failed", "cancelled", "expired"]:
            raise BatchError(f"Batch failed: {batch.status}")

        await asyncio.sleep(poll_interval)
```

### Structured Output with JSON Schema

```python
# Define schema for classification
CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "match": {"type": "boolean"},
        "conf": {"type": "number", "minimum": 0, "maximum": 1},
        "topic": {"type": "string"},
        "reason": {"type": "string", "maxLength": 100}
    },
    "required": ["match", "conf", "topic", "reason"]
}

async def classify_article(
    self,
    title: str,
    url: str
) -> ClassificationResult:
    """Classify article with structured output."""

    messages = [
        {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": f"Title: {title}\nURL: {url}"}
    ]

    response = await self.complete(
        messages=messages,
        model="gpt-5-nano",
        response_format={"type": "json_schema", "schema": CLASSIFICATION_SCHEMA}
    )

    data = json.loads(response)
    return ClassificationResult(**data)
```

### Error Handling & Retries

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import APIError, RateLimitError, APIConnectionError

class OpenAIClient:
    @retry(
        retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def complete_with_retry(self, **kwargs):
        """Call API with automatic exponential backoff retry."""
        return await self.complete(**kwargs)
```

### Cost Tracking

```python
class CostTracker:
    PRICING = {
        "gpt-5-nano": {"input": 0.003, "output": 0.006},  # $ per 1M tokens
        "gpt-4o-mini": {"input": 0.005, "output": 0.010}
    }

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate API call cost."""

        prices = self.PRICING.get(model, self.PRICING["gpt-4o-mini"])

        input_cost = (input_tokens / 1_000_000) * prices["input"]
        output_cost = (output_tokens / 1_000_000) * prices["output"]

        return input_cost + output_cost

    def track_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        run_id: str,
        module: str
    ):
        """Track API call in database."""

        cost = self.calculate_cost(model, input_tokens, output_tokens)

        # Store in database
        self.db.add(APICall(
            run_id=run_id,
            module=module,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        ))
```

## News Source Integration

### RSS Feed Handling

```python
import feedparser
from datetime import datetime, timedelta

class RSSCollector:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def collect(self, feed_url: str, max_age_hours: int = 24) -> List[Article]:
        """Collect articles from RSS feed."""

        # Parse feed with bozo tolerance
        feed = feedparser.parse(
            feed_url,
            agent="NewsAnalysis/2.0 (creditreform.ch)",
            request_headers={"Accept-Language": "de-CH, de, en"}
        )

        # Handle malformed feeds
        if feed.bozo and not feed.entries:
            raise FeedParseError(f"Failed to parse feed: {feed.bozo_exception}")

        # Filter by age
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        articles = []

        for entry in feed.entries:
            published = self.parse_date(entry.get("published"))

            if published and published > cutoff:
                articles.append(self.create_article(entry))

        return articles

    def parse_date(self, date_string: str) -> Optional[datetime]:
        """Parse RSS date (multiple formats)."""
        # Handle various RSS date formats
        # feedparser.parse provides parsed_date
        pass
```

### HTTP Client Configuration

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class HTTPClient:
    def __init__(self, timeout: int = 10, max_retries: int = 3):
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.timeout = timeout

    def get(self, url: str, headers: dict = None) -> requests.Response:
        """GET request with timeout and retry."""

        default_headers = {
            "User-Agent": "NewsAnalysis/2.0 (creditreform.ch)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "de-CH, de, en",
            "Accept-Encoding": "gzip, deflate"  # NOT zstd!
        }

        if headers:
            default_headers.update(headers)

        return self.session.get(
            url,
            headers=default_headers,
            timeout=self.timeout
        )
```

### Rate Limiting

```python
from asyncio import Semaphore
import time

class RateLimiter:
    def __init__(self, calls_per_second: float = 2.0):
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0
        self.semaphore = Semaphore(1)

    async def acquire(self):
        """Wait for rate limit."""

        async with self.semaphore:
            now = time.time()
            time_since_last = now - self.last_call

            if time_since_last < self.min_interval:
                await asyncio.sleep(self.min_interval - time_since_last)

            self.last_call = time.time()

# Usage
rate_limiter = RateLimiter(calls_per_second=2.0)

async def fetch_with_rate_limit(url: str):
    await rate_limiter.acquire()
    return await http_client.get(url)
```

### Robots.txt Compliance

```python
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

class RobotsChecker:
    def __init__(self):
        self.parsers = {}  # Cache robots.txt by domain

    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """Check if URL can be fetched per robots.txt."""

        domain = urlparse(url).netloc
        parser = self.get_parser(domain)

        return parser.can_fetch(user_agent, url)

    def get_parser(self, domain: str) -> RobotFileParser:
        """Get cached robots.txt parser for domain."""

        if domain not in self.parsers:
            parser = RobotFileParser()
            parser.set_url(f"https://{domain}/robots.txt")

            try:
                parser.read()
            except Exception:
                # Assume allowed if robots.txt unavailable
                pass

            self.parsers[domain] = parser

        return self.parsers[domain]
```

## Content Extraction

### Trafilatura (Primary Method)

```python
import trafilatura

def extract_with_trafilatura(url: str) -> Optional[str]:
    """Extract article content using Trafilatura."""

    downloaded = trafilatura.fetch_url(url)

    if not downloaded:
        return None

    content = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=True,
        include_formatting=False,
        favor_recall=True,  # High recall for Swiss news
        target_language="de"
    )

    return content
```

### Playwright Fallback (JavaScript-Heavy Sites)

```python
from playwright.async_api import async_playwright

async def extract_with_playwright(url: str) -> Optional[str]:
    """Extract content using Playwright (browser automation)."""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navigate with timeout
            await page.goto(url, timeout=12000, wait_until="networkidle")

            # Handle cookie consent (common on Swiss news sites)
            try:
                await page.click('button:has-text("Akzeptieren")', timeout=2000)
            except Exception:
                pass  # Consent button not found, continue

            # Extract main content
            content = await page.evaluate("""() => {
                const selectors = [
                    'article',
                    '.article-content',
                    '[role="article"]',
                    'main'
                ];

                for (const selector of selectors) {
                    const element = document.querySelector(selector);
                    if (element) return element.innerText;
                }

                return null;
            }""")

            return content

        finally:
            await browser.close()
```

## Circuit Breaker Pattern

Prevent cascading failures when external services fail:

```python
from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""

        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpen("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)

            # Success - reset if half-open
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0

            return result

        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

            raise

# Usage
openai_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

async def call_openai_with_breaker(**kwargs):
    return await openai_breaker.call(openai_client.complete, **kwargs)
```

## Monitoring & Alerts

### API Health Checks

```python
class APIHealthMonitor:
    def __init__(self):
        self.metrics = {
            "openai": {"success": 0, "failure": 0, "total_cost": 0.0},
            "news_sources": {}
        }

    def record_api_call(
        self,
        service: str,
        success: bool,
        cost: float = 0.0
    ):
        """Record API call metrics."""

        if service not in self.metrics:
            self.metrics[service] = {"success": 0, "failure": 0}

        if success:
            self.metrics[service]["success"] += 1
        else:
            self.metrics[service]["failure"] += 1

        if "total_cost" in self.metrics[service]:
            self.metrics[service]["total_cost"] += cost

    def get_health_status(self) -> dict:
        """Get health status for all services."""

        status = {}

        for service, metrics in self.metrics.items():
            total = metrics["success"] + metrics["failure"]
            success_rate = metrics["success"] / total if total > 0 else 0

            status[service] = {
                "healthy": success_rate > 0.95,
                "success_rate": success_rate,
                "total_calls": total
            }

        return status
```

## Best Practices

1. **Always use timeout**: Prevent hanging requests
2. **Implement retry with exponential backoff**: Handle transient failures
3. **Track costs in real-time**: OpenAI API costs accumulate quickly
4. **Use circuit breakers**: Prevent cascading failures
5. **Respect rate limits**: Both internal and external
6. **Cache aggressively**: Reduce API calls
7. **Use batch API when possible**: 50% cost savings
8. **Monitor API health**: Alert on high failure rates
9. **Handle errors gracefully**: Continue pipeline with partial results
10. **Validate API responses**: Ensure data quality

## Next Steps

- Review configuration management (07-configuration-management.md)
- Understand cost tracking implementation
- Implement OpenAI client with retry logic
