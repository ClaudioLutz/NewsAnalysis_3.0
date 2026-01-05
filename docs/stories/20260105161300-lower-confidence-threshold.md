# Lower AI Filter Confidence Threshold

## Summary

Reduced the AI classification confidence threshold from 0.71 to 0.70 to capture borderline-relevant articles about economic indicators and regulatory compliance.

## Context / Problem

Analysis of filtered articles revealed 3 articles scoring exactly 0.70 that were being rejected despite being relevant to Creditreform's focus areas:
- Swiss PMI (Einkaufsmanagerindex) decline article
- Liechtenstein trustees and US sanctions (regulatory compliance)
- Economic weakness and job market shifts

The LLM produces a bimodal distribution - articles are either clearly irrelevant (< 0.30) or relevant (>= 0.70), making 0.70 the natural boundary.

## What Changed

- Modified `config/topics.yaml`: `confidence_threshold: 0.71` → `confidence_threshold: 0.70`

## How to Test

1. Run the pipeline: `newsanalysis run`
2. Check that articles with confidence >= 0.70 are now included
3. Verify no increase in false positives (irrelevant articles passing through)

## Risk / Rollback Notes

- **Risk**: Minimal - only affects articles at exactly 0.70 confidence (rare edge case)
- **Rollback**: Change `confidence_threshold` back to `0.71` in `config/topics.yaml`
- **Monitoring**: Review matched articles in next few runs to ensure quality remains high
