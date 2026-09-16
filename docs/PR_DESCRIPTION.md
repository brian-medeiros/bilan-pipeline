## Summary

Extract 12 financial field types from the 15 Bilan filings using the supplied OCR and PDF geometry. The local pipeline processes 415 pages and emits 117 grounded fields, with conservative omissions, explicit formula components and measured runtime/API cost.

The implementation handles fiscal forms, ordinary statements and rotated panels. It documents schema interpretation ambiguities and distinguishes Bernachon's EUR main statements from its kEUR subsidiary tables. A reviewed rejection list omits an incomplete OCR total without supplying replacement financial values.

## Validation

- Official JSON Schema and additional PDF, metadata, numeric, unit and geometry checks.
- Automated unit/integration tests and formatting/static checks.
- 14 balance reconciliations and 18 explicitly dated temporal comparisons.
- AI-assisted visual review of the emitted evidence across all five companies; no independent human accuracy estimate.

See README.md, reports/summary.md and reports/visual_audit.json for reproducible commands, actual measurements and limitations.
