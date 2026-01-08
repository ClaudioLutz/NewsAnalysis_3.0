# Add Dedicated Data Protection (DSG) Topic Classification

## Summary

Added `data_protection` as a dedicated focus area and topic category, separating Swiss Data Protection Act (DSG/nDSG) content from general regulatory compliance for improved visibility in email digests.

## Context / Problem

Data protection (Datenschutzgesetz) news was previously bundled under `regulatory_compliance` alongside FINMA, Basel III, and GwG content. Given the importance of DSG compliance and the new Swiss Data Protection Act (nDSG/revDSG), data protection deserves its own dedicated topic for:
- Better filtering and prioritization of privacy-related news
- Dedicated section in email digests
- Improved classification accuracy for Bundesgericht rulings on data protection matters

## What Changed

### config/topics.yaml
- Added new `data_protection` focus area with comprehensive keywords:
  - DSG, Datenschutzgesetz, nDSG, revDSG
  - EDÖB (Federal Data Protection Commissioner)
  - Personendaten, Datenbearbeitung, Datenweitergabe
  - Auskunftsrecht, Löschungsrecht, Einwilligung
  - Datenschutzverletzung, DSGVO, Privacy, Datensicherheit
- Removed `nDSG` and `Datenschutz` from `regulatory_compliance` (now in `data_protection`)

### config/prompts/classification.yaml
- Added dedicated line: "Data protection (DSG, nDSG, EDÖB, Datenschutz, Personendaten, DSGVO, Datenschutzverletzung)"
- Removed `nDSG` from regulatory_compliance line

### config/prompts/summarization.yaml
- Added `data_protection` to topic enum in both user prompt template and output schema

### src/newsanalysis/core/enums.py
- Added `DATA_PROTECTION = "data_protection"` to `ArticleTopic` enum

### src/newsanalysis/pipeline/formatters/german_formatter.py
- Added `"data_protection"` to `TOPIC_PRIORITY` list (after regulatory_compliance)
- Added German translation: `"data_protection": "Datenschutz"` to `TOPIC_TRANSLATIONS`

## How to Test

1. Run classification on a DSG-related article:
   ```bash
   newsanalysis run --collect-only
   ```

2. Verify articles mentioning DSG/EDÖB/Datenschutz are classified as `data_protection` (not `regulatory_compliance`)

3. Check email digest has separate Data Protection section

## Risk / Rollback Notes

- **Risk**: Existing articles classified as `regulatory_compliance` with DSG content won't be reclassified automatically. Only new articles will use the new topic.
- **Risk**: If email template groups topics, may need update to handle `data_protection` display name.
- **Rollback**: Revert changes in all five files (topics.yaml, classification.yaml, summarization.yaml, enums.py, german_formatter.py) and move keywords back to `regulatory_compliance`.
