# Harden Classification Prompt for Swiss-Focused Credit Risk Analysis

## Summary

Completely rewrote the classification prompt to enforce Swiss-first geographic filtering, strict topic enumeration, and explicit rejection criteria. Added new `business_scams` topic category. Reduced topic inconsistency from 287 unique values to 13 consistent values.

## Context / Problem

The existing classification prompt had several issues causing poor article selection quality:

1. **Topic inconsistency**: The topic field was unconstrained, resulting in 287 unique topic values including:
   - Mixed case variations: `Economic indicators` vs `economic_indicators` vs `Economic Indicators`
   - Irrelevant topics: `Sports` (108 articles), `Weather`, `Astronomy and Cosmology`
   - Catch-all overuse: `other` (14 articles), `Not applicable`, `General News`

2. **No clear rejection criteria**: The prompt only listed what to include, not what to explicitly reject (sports, weather, entertainment, etc.)

3. **Vague geographic scope**: "Swiss and European business news" was too broad, accepting non-Swiss articles

4. **Missing fraud category**: Business scams, CEO-fraud, and investment fraud had no dedicated topic

5. **Weak match decision rules**: No clear threshold for when to accept vs reject

## What Changed

### config/prompts/classification.yaml (Complete Rewrite)
- Added Creditreform context (credit risk reports, debt collection, payment behavior)
- **Geographic scope**: Swiss-first with explicit accept/reject criteria
- **13 topic definitions** with German keywords and example headlines:
  - `insolvency_bankruptcy`, `credit_risk`, `regulatory_compliance`, `data_protection`
  - `kyc_aml_sanctions`, `payment_behavior`, `debt_collection`, `board_changes`
  - `company_lifecycle`, `economic_indicators`, `market_intelligence`, `ecommerce_fraud`
  - `business_scams` (NEW)
- **Explicit rejection criteria**: Sports, weather, entertainment, personal crimes, international politics
- **Decision rules**: Three conditions that ALL must be true for match=true
- **Topic enum constraint** in output_schema with `rejected` for non-matches

### config/prompts/summarization.yaml
- Added `business_scams` to topic enum
- Removed `other` as fallback option

### src/newsanalysis/core/enums.py
- Added `BUSINESS_SCAMS = "business_scams"` to ArticleTopic
- Removed `OTHER = "other"`

### src/newsanalysis/pipeline/formatters/german_formatter.py
- Added `business_scams` to `TOPIC_PRIORITY`
- Added translation: `"business_scams": "Wirtschaftsdelikte"`
- Renamed `ecommerce_fraud` translation to `"Online-Betrug"`
- Kept `other` in legacy mappings for backwards compatibility

### src/newsanalysis/pipeline/summarizers/article_summarizer.py
- Changed default topic from `OTHER` to `MARKET_INTELLIGENCE`
- Updated fallback topic in cache retrieval and API response parsing

### src/newsanalysis/cli/commands/run.py
- Fixed `--reset all` SQL to use correct column names (`is_match`, `filtered_at` instead of `classification_decision`, `classified_at`)

### tests/unit/test_models.py
- Updated `test_article_topic_valid_values` to test `business_scams`
- Changed test count from 12 to 13 topics
- Updated default topic test to expect `MARKET_INTELLIGENCE`

## Results

| Metric | Before | After |
|--------|--------|-------|
| Unique topic values | 287 | 13 |
| "other" catchall | 14 articles | 0 articles |
| Match rate | 5.0% (59/1187) | 7.0% (83/1187) |
| Topic consistency | Poor (mixed case, free-form) | Perfect (enum-constrained) |

### Topic Distribution (After)
```
 36  economic_indicators     (Swiss economy)
 18  company_lifecycle       (restructuring, M&A)
  9  regulatory_compliance   (FINMA, regulations)
  4  insolvency_bankruptcy   (bankruptcies)
  4  board_changes           (management changes)
  3  market_intelligence     (industry trends)
  3  credit_risk
  2  kyc_aml_sanctions
  2  ecommerce_fraud
  2  business_scams
```

### Previously Rejected, Now Correctly Matched
- "radicant bank Appoints Matthias Kottmann as Chairman" -> `board_changes`
- "Dormakaba rüstet Flughäfen Frankfurt, München" -> `company_lifecycle`
- "Rheinschifffahrt – Privatfirma darf Basler..." -> `company_lifecycle`
- "Finanzberatungsfirma bedrängt..." -> `business_scams`

### Correctly Rejected
- Sports (ski racing, tennis, football)
- Weather/natural disasters
- International politics (Venezuela, Greenland)
- Entertainment, culture, science

## How to Test

1. Clear classification cache and re-run:
   ```bash
   python -m newsanalysis.cli.main run --reset all --skip-collection --limit 50
   ```

2. Check topic distribution:
   ```python
   import sqlite3
   conn = sqlite3.connect('news.db')
   cursor = conn.cursor()
   cursor.execute('''
       SELECT topic, COUNT(*)
       FROM articles WHERE is_match = 1
       GROUP BY topic ORDER BY COUNT(*) DESC
   ''')
   for row in cursor.fetchall():
       print(f'{row[1]:3d}  {row[0]}')
   ```

3. Verify all topics are lowercase snake_case (no mixed case)

4. Check email digest has proper topic sections

## Risk / Rollback Notes

- **Risk**: Stricter filtering may reduce article count. Monitor match rate over time.
- **Risk**: Existing articles with legacy topics (e.g., `Economic indicators`) will display correctly due to legacy mappings but won't be re-classified automatically.
- **Risk**: The `business_scams` vs `ecommerce_fraud` distinction may need tuning based on real-world classification results.
- **Rollback**: Revert commit `1500c7c` which contains all changes.
