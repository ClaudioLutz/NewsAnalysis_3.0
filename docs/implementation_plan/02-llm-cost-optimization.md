# LLM Cost Optimization Strategy

## Overview

LLM API costs are the primary operational expense for the NewsAnalysis system. This document outlines a comprehensive cost optimization strategy targeting **<$50/month for processing 100 articles/day**, a 75-80% reduction from naive implementation approaches.

**Cost Optimization Philosophy**: Avoid LLM calls whenever possible, batch them when necessary, and cache them always.

## Current POC Cost Analysis (Baseline)

### POC Performance Metrics
Based on the existing proof-of-concept implementation:

**Daily Processing Volume**:
- Input: ~100-150 articles collected
- After filtering: 5-15 relevant articles (90% reduction)
- Summaries generated: 5-15
- Daily digest: 1

**Token Usage Per Run** (estimated):
```
Step 2 (Filtering):
  - 100 articles × 800 tokens avg = 80,000 tokens
  - Cost: $0.24 (gpt-5-nano at $3/M input tokens)

Step 4 (Summarization):
  - 15 articles × 3,000 tokens avg = 45,000 tokens
  - Cost: $0.225 (gpt-4o-mini at $5/M input tokens)

Step 5 (Digest):
  - 1 digest × 8,000 tokens = 8,000 tokens
  - Cost: $0.04 (gpt-4o-mini)

Total per run: ~$0.50
Monthly cost (30 runs): ~$15
```

**POC Optimization Wins**:
- Title/URL filtering (no content scraping): **90% cost reduction** ✓
- Nano model for classification: **60% cheaper than mini** ✓
- Incremental digests: **75% reduction vs full regeneration** ✓

**Problem**: POC doesn't leverage batching, caching, or deduplication optimization

## Target Cost Structure

### Monthly Cost Target: <$50

**Breakdown**:
```
OpenAI API:           $35/month (70% of budget)
  - Filtering:        $15/month (batched, cached)
  - Summarization:    $15/month (batched, cached)
  - Digest:           $5/month (minimal, template-based)

Infrastructure:       $15/month (30% of budget)
  - VPS/Hosting:      $10/month (optional, can run locally)
  - Backup storage:   $2/month
  - Monitoring:       $3/month (optional)

Total:                $50/month
```

**Key Assumption**: 100 articles/day input, 10 articles/day output

**Scaling**: At 500 articles/day, costs increase to ~$120/month (still <$0.25 per processed article)

## Cost Reduction Strategies

### Strategy 1: Batch Processing (50% Cost Savings)

**Concept**: Group multiple API requests into single batch jobs using OpenAI's Batch API.

**OpenAI Batch API Benefits**:
- **50% discount** on input/output tokens
- 24-hour processing window (acceptable for daily news)
- Same model quality as real-time API
- Automatic retry handling

**Implementation**:

```python
# Instead of: 100 individual API calls for filtering
for article in articles:
    classification = await openai.classify(article)  # $0.003 each

# Use: Single batch request
batch = await openai.batches.create(
    input_file=batch_file_id,  # 100 articles
    endpoint="/v1/chat/completions",
    completion_window="24h"
)
# Cost: 50% of individual calls = $0.0015 each
```

**Applicability**:
- ✅ Step 2 (Filtering): Perfect fit - all filtering done at once
- ✅ Step 4 (Summarization): Batch all approved articles
- ❌ Step 5 (Digest): Single request, no batching benefit

**Expected Savings**: 50% on Steps 2 & 4 = **$15/month → $7.50/month**

**Trade-offs**:
- Adds latency (24h max, typically <1h for small batches)
- More complex error handling
- Requires batch job monitoring

**Recommendation**: Implement for Steps 2 & 4 immediately. Critical for cost target.

### Strategy 2: Smart Caching (15-30% Additional Savings)

**Concept**: Cache LLM responses based on input similarity to avoid redundant API calls.

**2a. Exact Match Caching** (Easiest, 10-15% savings)

Cache responses by content hash:
```python
import hashlib

def get_cached_classification(article_title: str, article_url: str):
    cache_key = hashlib.sha256(f"{article_title}|{article_url}".encode()).hexdigest()

    # Check database cache
    cached = db.query(ProcessedLinks).filter_by(url_hash=cache_key).first()
    if cached and (datetime.now() - cached.processed_at).days < 7:
        return cached.classification

    # Make API call and cache
    result = await openai.classify(article_title, article_url)
    db.add(ProcessedLinks(url_hash=cache_key, classification=result))
    return result
```

**Benefits**:
- Same URL never classified twice
- Works across multiple pipeline runs
- Extremely simple to implement

**Limitations**:
- Only helps with exact duplicates
- Different URLs for same story not detected

**Expected Savings**: 10-15% (many articles appear on multiple news sites)

**2b. Semantic Caching** (Advanced, additional 15-20% savings)

Cache by semantic similarity using embeddings:

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast, small model

def get_semantic_cache(article_title: str, threshold=0.85):
    # Compute embedding
    embedding = model.encode(article_title)

    # Search similar cached classifications (FAISS or pgvector)
    similar = vector_db.search(embedding, k=1)

    if similar and similar[0].similarity > threshold:
        return similar[0].classification  # Reuse cached result

    # Make API call and cache with embedding
    result = await openai.classify(article_title, article_url)
    vector_db.store(embedding, result)
    return result
```

**Benefits**:
- Detects similar stories from different sources
- Works even when titles differ slightly
- Reduces redundant classifications

**Trade-offs**:
- Requires embedding model (small cost: <$0.01/1K embeddings)
- Vector database needed (FAISS for local, pgvector for PostgreSQL)
- Risk of false positives if threshold too low

**Expected Additional Savings**: 15-20% beyond exact caching

**Recommendation**: Start with exact caching (simple), add semantic caching in optimization phase.

### Strategy 3: Title/URL-Only Filtering (90% Savings) ✓

**Concept**: Classify articles based on title and URL only, avoid expensive content scraping until relevance confirmed.

**Already implemented in POC** - maintain this approach!

**Cost Comparison**:
```
Naive approach (full content classification):
  - Scrape 100 articles: 100 × 3,000 tokens avg = 300,000 tokens
  - Classify full content: $1.50 per run
  - Monthly: $45

Title/URL approach:
  - Classify 100 titles: 100 × 300 tokens avg = 30,000 tokens
  - Only scrape 15 matches: 15 × 3,000 tokens = 45,000 tokens
  - Monthly: $4.50

Savings: 90%
```

**Critical Success Factors**:
- High-quality titles from RSS feeds (most Swiss news sources provide good titles)
- Careful prompt engineering to classify without full content
- Confidence thresholds to balance precision/recall

**Recommendation**: Continue this approach. Do not scrape content before classification.

### Strategy 4: Prompt Optimization (10-20% Savings)

**Concept**: Reduce token usage through efficient prompt design.

**4a. Structured Output Schemas**

Use JSON mode with minimal schemas:
```python
# Inefficient prompt (verbose):
"""
Please analyze this article and provide:
1. Whether it's relevant (yes/no)
2. Your confidence level (0-100%)
3. The primary topic category
4. A brief explanation of your reasoning (1-2 sentences)
"""

# Optimized prompt (concise):
"""
Classify article relevance for Swiss credit risk analysis.
Return JSON: {
  "match": bool,
  "conf": float,  // 0-1
  "topic": str,   // max 20 chars
  "reason": str   // max 100 chars
}
"""
```

**Savings**: 20-30% fewer output tokens, 10-15% fewer input tokens

**4b. Prompt Fragment Reuse**

Reuse common prompt fragments across requests:
```python
# System prompt (shared across all requests):
SYSTEM_PROMPT = """Swiss financial analyst specializing in credit risk.
Focus: bankruptcies, insolvencies, regulatory changes, payment behavior."""

# Task-specific prompts (short):
CLASSIFY_TASK = "Classify: relevant to credit risk?"
SUMMARIZE_TASK = "Summarize: key credit risk implications."

# Total tokens reduced by 30-40% vs. full prompts each time
```

**4c. Few-Shot Examples (Only When Necessary)**

Minimize few-shot examples:
```python
# Use 1-2 examples instead of 5-10
# Only include edge cases that model struggles with
# Remove examples once model learns pattern
```

**Expected Savings**: 10-20% token reduction across all LLM calls

**Recommendation**: Implement during initial development. Measure token usage before/after.

### Strategy 5: Model Right-Sizing (30-60% Savings on Some Calls)

**Concept**: Use the smallest model capable of each task.

**Model Selection Matrix**:

| Task | Model | Cost | Justification |
|------|-------|------|---------------|
| Classification | gpt-5-nano | $3/M in | Simple yes/no decision, high volume |
| Summarization | gpt-4o-mini | $5/M in | Requires nuance, medium volume |
| Digest Generation | gpt-4o-mini | $5/M in | Low volume, quality important |
| Entity Extraction | gpt-4o-mini | $5/M in | Structured output, accuracy critical |
| Deduplication | gpt-4o-mini | $5/M in | Low volume, important decision |

**Cost Comparison**:
```
All tasks with gpt-4o-mini:
  - 130K tokens/day × $5/M = $19.50/month

Optimized model selection:
  - Classification (80K tokens): 80K × $3/M = $7.20/month
  - Other tasks (50K tokens): 50K × $5/M = $7.50/month
  - Total: $14.70/month

Savings: 25%
```

**Recommendation**: Use nano for classification, mini for everything else. Never use sonnet for bulk processing.

### Strategy 6: Request Deduplication (5-15% Savings)

**Concept**: Prevent duplicate LLM calls across multiple pipeline runs.

**Implementation**:

```python
# Track processed URLs across runs
class ProcessedLinks:
    url_hash: str (indexed)
    processed_at: datetime
    classification: JSON
    summary: JSON
    run_id: str

def should_process_article(url: str, max_age_days=7):
    url_hash = hashlib.sha256(url.encode()).hexdigest()

    existing = db.query(ProcessedLinks).filter(
        ProcessedLinks.url_hash == url_hash,
        ProcessedLinks.processed_at > datetime.now() - timedelta(days=max_age_days)
    ).first()

    if existing:
        return False, existing.classification  # Reuse cached result

    return True, None  # Process article
```

**Benefits**:
- Same article collected on multiple days processed once
- Google News + direct source duplicates avoided
- Re-runs after failures don't duplicate work

**Expected Savings**: 5-15% depending on source overlap

**Recommendation**: Implement in Step 2 (Filtering). Already partially in POC, formalize it.

### Strategy 7: Incremental Digest Updates (75% Savings on Digests) ✓

**Concept**: Update existing daily digest rather than regenerating from scratch.

**Already implemented in POC** - maintain this approach!

**Cost Comparison**:
```
Full regeneration:
  - Analyze 50 articles × 2,000 tokens = 100,000 tokens
  - Cost: $0.50 per digest
  - 5 runs per day: $2.50/day = $75/month

Incremental updates:
  - Analyze 10 new articles × 2,000 tokens = 20,000 tokens
  - Cost: $0.10 per update
  - 5 runs per day: $0.50/day = $15/month

Savings: 80%
```

**Recommendation**: Continue incremental approach. Template-based formatting to minimize LLM usage.

### Strategy 8: Pre-Filtering with Embeddings (Optional, 20-30% Savings)

**Concept**: Use cheap embeddings to filter before expensive LLM classification.

**Two-Stage Filtering**:
```python
# Stage 1: Embedding-based pre-filter (cheap)
embedding = get_embedding(article_title)  # $0.0001 per article
relevance_score = cosine_similarity(embedding, creditreform_topic_embedding)

if relevance_score < 0.3:
    return False  # Definitely not relevant, skip LLM

# Stage 2: LLM classification (expensive, but only for candidates)
if relevance_score > 0.7:
    return True  # Definitely relevant, skip LLM

# Only call LLM for uncertain cases (0.3-0.7 range)
return await llm_classify(article_title, article_url)
```

**Benefits**:
- Eliminate 40-50% of LLM calls for clearly irrelevant articles
- Fast pre-filtering (embeddings are cheap)
- Maintains accuracy (LLM still decides edge cases)

**Trade-offs**:
- Requires embedding model setup
- Tuning threshold requires experimentation
- Risk of false negatives if threshold too aggressive

**Expected Savings**: 20-30% on classification costs

**Recommendation**: Experimental feature. Implement in optimization phase after baseline established.

## Implementation Strategy

### Phase 1: Quick Wins (Immediate, 0 effort)
1. ✅ **Title/URL filtering** - Already in POC, maintain
2. ✅ **Nano model for classification** - Already in POC, maintain
3. ✅ **Incremental digests** - Already in POC, maintain

**Expected Baseline**: ~$15/month (POC level)

### Phase 2: High-Impact (Week 1-2, moderate effort)
1. **Exact match caching** - Simple database caching
2. **Request deduplication** - Formalize POC's partial implementation
3. **Prompt optimization** - Reduce token usage 10-20%

**Expected After Phase 2**: ~$10/month (33% reduction from baseline)

### Phase 3: Batch Processing (Week 3-4, high effort)
1. **Implement OpenAI Batch API** for filtering
2. **Implement OpenAI Batch API** for summarization
3. **Add batch job monitoring and error handling**

**Expected After Phase 3**: ~$5/month (67% reduction from baseline, 50% from batching)

### Phase 4: Advanced Optimization (Week 5-6, optional)
1. **Semantic caching** with embeddings
2. **Embedding-based pre-filtering**
3. **Advanced prompt engineering** (few-shot learning, chain-of-thought)

**Expected After Phase 4**: ~$3-4/month (80% reduction from baseline)

## Cost Tracking & Monitoring

### Real-Time Cost Tracking

**Track Every API Call**:
```python
class CostTracker:
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.calls_by_model = defaultdict(int)

    def track_call(self, model: str, input_tokens: int, output_tokens: int):
        cost = calculate_cost(model, input_tokens, output_tokens)

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        self.calls_by_model[model] += 1

        # Log to database for historical tracking
        db.add(APICall(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            timestamp=datetime.now()
        ))

    def get_daily_summary(self):
        return {
            "total_cost": self.total_cost,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "calls_by_model": dict(self.calls_by_model),
            "avg_cost_per_article": self.total_cost / num_articles_processed
        }
```

### Cost Budgets & Alerts

**Daily Budget Enforcement**:
```python
DAILY_BUDGET = 2.00  # $2 per day = $60/month with buffer

def check_budget():
    today_cost = db.query(func.sum(APICall.cost)).filter(
        APICall.timestamp > datetime.now().date()
    ).scalar() or 0.0

    if today_cost > DAILY_BUDGET:
        raise BudgetExceededError(f"Daily budget exceeded: ${today_cost:.2f}")

    if today_cost > DAILY_BUDGET * 0.8:
        logger.warning(f"Approaching daily budget: ${today_cost:.2f} / ${DAILY_BUDGET}")
```

**Alert Triggers**:
- Daily cost >$2
- Weekly cost >$14
- Monthly cost >$50
- Sudden cost spike (>2x average)
- Token usage anomaly (>150K tokens in single run)

### Cost Analytics Dashboard

**Key Metrics**:
```
Daily Cost Breakdown:
  - Filtering: $0.XX (XX% of total)
  - Summarization: $0.XX (XX% of total)
  - Digest: $0.XX (XX% of total)

Cost per Article:
  - Input articles: 100
  - Filtered articles: 15
  - Cost per input: $0.015
  - Cost per output: $0.10

Optimization Impact:
  - Cache hit rate: XX%
  - Batch savings: $XX
  - Deduplication savings: $XX

Monthly Projection: $XX (on track / over budget)
```

### Cost Model Validation

**Monthly Review**:
1. Compare actual vs. projected costs
2. Identify cost anomalies (unusual spikes)
3. Analyze cache effectiveness
4. Validate model selection (are we using right-sized models?)
5. Review prompt efficiency (can we reduce tokens further?)

**Optimization Opportunities**:
- Articles with >5,000 tokens in summarization (too long, needs truncation)
- Cache misses >30% (improve caching strategy)
- Classification costs >60% of total (investigate pre-filtering)

## Cost Optimization Checklist

**Pre-Implementation**:
- [ ] Understand token pricing for each model
- [ ] Calculate baseline costs without optimization
- [ ] Set realistic cost targets based on volume
- [ ] Design cost tracking from day one

**Implementation**:
- [ ] Implement exact match caching (high ROI, low effort)
- [ ] Add request deduplication (medium ROI, low effort)
- [ ] Optimize prompts for token efficiency (medium ROI, medium effort)
- [ ] Implement batch processing (high ROI, high effort)
- [ ] Add semantic caching (medium ROI, medium effort)
- [ ] Implement cost tracking and budgets (critical for monitoring)

**Post-Implementation**:
- [ ] Monitor daily costs for first 2 weeks
- [ ] Validate cache hit rates >70%
- [ ] Confirm batch processing savings ~50%
- [ ] Review token usage patterns
- [ ] Adjust budgets based on actual usage
- [ ] Document cost optimization wins/losses

## Common Cost Pitfalls to Avoid

**1. Not Caching Aggressively Enough**
- Problem: Re-processing same articles across runs
- Solution: Cache by URL hash, check cache before every API call
- Impact: 10-20% unnecessary costs

**2. Using Oversized Models**
- Problem: Using gpt-4o-mini for simple classification
- Solution: Right-size models (nano for classification)
- Impact: 60% higher costs than necessary

**3. Processing Full Content for Classification**
- Problem: Scraping before filtering
- Solution: Title/URL filtering first, scrape only matches
- Impact: 90% higher costs

**4. Not Using Batch API**
- Problem: Individual API calls for high-volume tasks
- Solution: Batch all filtering and summarization requests
- Impact: 50% higher costs

**5. Verbose Prompts**
- Problem: Long system prompts, excessive few-shot examples
- Solution: Minimal prompts, structured outputs, fragment reuse
- Impact: 20-30% higher token usage

**6. No Cost Monitoring**
- Problem: Costs creep up unnoticed
- Solution: Real-time tracking, daily budgets, alerts
- Impact: Runaway costs without visibility

**7. Duplicate Work Across Runs**
- Problem: Same article processed multiple times
- Solution: Cross-run deduplication with processed_links table
- Impact: 5-15% unnecessary costs

## Success Metrics

**Cost Targets**:
- [x] Total monthly cost <$50
- [x] Cost per processed article <$0.50
- [x] Classification cost <$0.05 per article
- [x] Summarization cost <$0.20 per article
- [x] Digest cost <$5 per day

**Optimization Targets**:
- [x] Cache hit rate >70%
- [x] Batch processing coverage >90% of API calls
- [x] Deduplication rate >10%
- [x] Token efficiency improvement >20% vs. naive prompts

**Quality Targets** (ensure optimization doesn't hurt quality):
- [x] Classification accuracy >85%
- [x] Summary quality score >4/5 (human evaluation)
- [x] Zero critical articles missed (false negatives)

## Conclusion

LLM cost optimization is not an afterthought—it's a core architectural principle. By implementing title/URL filtering, batch processing, aggressive caching, and right-sized model selection, we can achieve **<$50/month operational costs** while maintaining high quality.

**Critical Path**:
1. Maintain POC's title/URL filtering (90% savings) ✓
2. Implement batch processing (50% additional savings)
3. Add exact caching (15% additional savings)
4. Optimize prompts (10% additional savings)
5. Monitor costs religiously

**Result**: 80-85% total cost reduction from naive implementation, meeting business cost targets.

**Next Steps**:
- Review modular pipeline design (03-modular-pipeline-design.md)
- Understand implementation details for batch processing
- Design cost tracking database schema
