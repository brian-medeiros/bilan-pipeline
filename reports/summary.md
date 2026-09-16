# Bilan execution summary

- Processed documents: 15/15
- PDF/OCR pages processed: 415
- Emitted fields: 117/180 (65.0%)
- Structural/schema errors: 0
- Batch failures: 0
- Measured elapsed time: 6.333123 seconds
- Measured time/page: 0.01526054 seconds
- Marginal API cost/page: 0.0 EUR

Measured with perf_counter: discovery, PDF/OCR loading, extraction, structural and domain validation. Excludes installation, download, manual/visual QA and final report serialization. Zero marginal API cost; hardware, storage and upstream OCR cost are not estimated. Field content is deterministic; measured timings vary.

## Consistency proxies

- Balance reconciliations within one printed unit: 14/14
- Temporal checks within one printed unit: 18/18
- Exact temporal matches: 17/18

These are consistency checks, not an accuracy estimate. See visual_audit.json for the static AI-assisted review record.

## Coverage by field

| Field | Emitted filings |
|---|---:|
| PL_REVENUE_FRGAAP | 9 |
| PL_COGS_FRGAAP | 1 |
| PL_PERSONNEL_COSTS_FRGAAP | 10 |
| PL_EXT_SERVICES_COSTS_FRGAAP | 10 |
| PL_DEPRECIATION_AMORTIZATION_FRGAAP | 9 |
| PL_FINANCIAL_RESULTS_FRGAAP | 8 |
| PL_INCOME_TAX_FRGAAP | 9 |
| BS_TOTAL_ASSETS_FRGAAP | 14 |
| BS_TOTAL_EQUITY_FRGAAP | 12 |
| BS_CAPITAL_EQUITY_FRGAAP | 15 |
| BS_CASH_CURRENT_ASSET_FRGAAP | 15 |
| META_AVG_WORKFORCE_FRGAAP | 5 |

## Coverage by document

| SIREN | Closing date | Document ID | Fields |
|---|---|---|---:|
| 820561470 | 2021-08-31 | 6493e4372f502414800f8164 | 4 |
| 820561470 | 2022-08-31 | 6543d3fd08093cdace058668 | 4 |
| 820561470 | 2023-08-31 | 67458f18cea78a70070fa226 | 4 |
| 328024377 | 2020-06-30 | 63e8ebbb54febda17c19ee7c | 9 |
| 328024377 | 2021-06-30 | 63e8ebbb54febda17c19ee7d | 11 |
| 328024377 | 2022-06-30 | 63e8ebbb54febda17c19ee7e | 11 |
| 445070311 | 2020-06-30 | 63e2481c916269756a09542b | 8 |
| 445070311 | 2022-06-30 | 65a4095d5fd178b16b09b860 | 8 |
| 445070311 | 2023-06-30 | 6860f28ca0138eae340c7453 | 8 |
| 504304205 | 2016-12-31 | 63e13943526e1f30cd100db5 | 11 |
| 504304205 | 2017-12-31 | 63e13943526e1f30cd100db6 | 9 |
| 504304205 | 2020-12-31 | 66cd893cedec9b09d50191e8 | 5 |
| 401009741 | 2022-04-30 | 63e881158be6eb9f9d1ff975 | 11 |
| 401009741 | 2023-04-30 | 65784e5da67d84faf4042736 | 10 |
| 401009741 | 2025-04-30 | 68f0a715f28d8aaf48046416 | 4 |

## Temporal coverage

| SIREN | Filings considered | Explicit-date comparisons |
|---|---:|---:|
| 328024377 | 3 | 5 |
| 401009741 | 3 | 0 |
| 445070311 | 3 | 5 |
| 504304205 | 3 | 0 |
| 820561470 | 3 | 8 |
