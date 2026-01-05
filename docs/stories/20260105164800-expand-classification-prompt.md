# Expand Classification Prompt for Creditreform Services

## Summary

Enhanced the AI classification prompt to cover additional Creditreform Switzerland service areas including e-commerce fraud, company lifecycle events, debt collection enforcement, and KYC/AML compliance.

## Context / Problem

Analysis of the Creditreform Switzerland website (creditreform.ch) revealed service areas not covered by the original classification prompt:
- E-commerce fraud detection (RiskCUBE product)
- Company lifecycle events (founding, restructuring, bankruptcy)
- Legal debt collection (Betreibung, Pfändung)
- KYC/AML and sanctions compliance

These gaps could cause relevant articles to be filtered out.

## What Changed

**config/prompts/classification.yaml:**
- Expanded from 6 to 10 focus areas in system prompt
- Added: Company lifecycle events (Firmengründung, Firmenkonkurs, Restrukturierung, Turnaround, Handelsregister)
- Added: Debt collection enforcement (Betreibung, Pfändung)
- Added: KYC/AML and sanctions (Sanktionen, Due Diligence, Wirtschaftskriminalität)
- Added: E-commerce fraud (Online-Betrug, Fraud, Kreditkartenbetrug, Identitätsdiebstahl)
- Added Swiss/European focus guidance

**config/topics.yaml:**
- Added 5 new focus area categories to match the prompt
- Added: company_lifecycle, debt_collection, kyc_aml_sanctions, ecommerce_fraud
- Added "Firmenpleiten" to economic_indicators

## How to Test

1. Run the pipeline: `newsanalysis run`
2. Check classification results for articles mentioning:
   - Company bankruptcies or restructuring
   - Fraud or cybercrime
   - Sanctions or compliance violations
3. Verify these now receive higher confidence scores

## Risk / Rollback Notes

- **Risk**: Slight increase in matched articles (intended behavior)
- **Risk**: Minimal token cost increase (~20 extra tokens per classification)
- **Rollback**: Revert changes to `config/prompts/classification.yaml` and `config/topics.yaml`
- **Monitoring**: Compare match rates before/after to ensure quality remains high
