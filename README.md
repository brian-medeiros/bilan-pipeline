# Bilan pipeline

Extraction of 12 financial field types from French annual accounts, built for the [Takeovers Bilan challenge](challenges/bilan/BRIEF.md).

The pipeline uses the supplied OCR, financial labels and page coordinates to extract values from 15 filings. Each result includes its unit, source page and normalized bounding box. Missing or ambiguous values are omitted, with reasons recorded in the diagnostics.

## Results

| Measure | Recorded run |
|---|---:|
| Documents processed | 15 / 15 |
| Pages processed | 415 |
| Fields extracted | 117 / 180 (65%) |
| Field types represented | 12 / 12 |
| Schema validation errors | 0 |
| Automated tests passed | 45 |
| Balance reconciliations | 14 / 14 exact |
| Cross-filing comparisons | 18 / 18 within one printed unit |
| Total processing time | 3.855569 s |
| Processing time per page | 0.00929053 s |
| Marginal API cost per page | EUR 0.00 |

Output: [results.json](results.json). See the [execution report](reports/summary.md) for coverage by field and document.

**65% is coverage, not accuracy.** There is no independently annotated evaluation set. Reconciliation and regression tests check consistency; the visual review was AI-assisted and used during development. These checks do not establish an unbiased accuracy score.

## Quick start

Requires **Python 3.11+**. Run from a complete repository checkout containing `data/`, `challenges/`, `tools/` and `bilan_pipeline/`.

```bash
git clone https://github.com/brian-medeiros/bilan-pipeline.git
cd bilan-pipeline
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
source .venv/bin/activate
```

Install, extract and validate:

```bash
python -m pip install -r requirements.txt
python -m bilan_pipeline --data-dir data --output results.json
python -m bilan_pipeline --validate-only --output results.json
python -m pytest -q
```

No API keys or environment variables are required. [.env.example](.env.example) documents this. The original PDFs, OCR, schemas and viewer are preserved.

To inspect one document without replacing the full output:

```bash
python -m bilan_pipeline --doc-id 63e881158be6eb9f9d1ff975 --output tmp/one.json --reports-dir tmp/one-reports --log-level DEBUG
```

To render evidence boxes for inspection:

```bash
python -m bilan_pipeline.qa
```

Images are written to the ignored `qa/` directory. The [visual audit record](reports/visual_audit.json) identifies the output reviewed during development; rerunning extraction does not automatically approve new evidence.

## Approach

```text
Brief + PDF metadata + supplied OCR
  -> page/form classification and rotation handling
  -> current-year column and financial row selection
  -> number parsing, units and derived fields
  -> evidence boxes and validation
  -> results.json + diagnostic reports
```

The main choices are:

- **Reuse the supplied OCR.** This keeps runtime local and avoids additional OCR or inference charges.
- **Use labels and geometry together.** Row alignment, fiscal codes and date headers distinguish current-year values from N-1, gross amounts and percentage columns.
- **Require evidence for derived values.** Personnel costs use wages plus social charges. COGS requires every component of the documented challenge formula; missing components are not treated as zero.
- **Keep provenance.** OCR text, component values and coordinates remain available for debugging. Bounding boxes follow the official viewer's 300-dpi conversion.
- **Omit uncertain results.** Conflicts, damaged totals and insufficient evidence are reported instead of filled with estimates.

Implementation details, field definitions and confidence rules are in [Technical notes](docs/TECHNICAL_NOTES.md). The main modules are [extraction.py](bilan_pipeline/extraction.py), [field_catalog.py](bilan_pipeline/field_catalog.py) and [validation.py](bilan_pipeline/validation.py).

## Trade-offs and limitations

Local rules provide reproducible extraction, low measured latency and traceable evidence. The trade-off is lower coverage on damaged OCR and unfamiliar layouts. **63 of 180 document-field pairs are omitted**, including fields absent from the supplied filings. COGS is emitted for only one filing because all five required components must be readable.

The timer includes discovery, PDF/OCR loading, extraction and validation. It excludes installation, downloading, development, visual review and final report serialization. All 415 pages are counted, including 41 with no OCR lines. Timings depend on the machine and filesystem cache. The zero cost is **marginal runtime API cost**; hardware, upstream OCR and development tools are not priced.

Two findings matter when interpreting the output:

- **EUR versus kEUR:** the extracted Bernachon main statements declare euros; the kilo-euro declarations apply to subsidiary tables or individual amounts. Unit scope is recorded in the diagnostics. The submitted monetary fields are therefore EUR. Page references and the reasoning are documented in [Technical notes](docs/TECHNICAL_NOTES.md#unit-detection-a-material-finding).
- **Damaged totals:** one Bockel page loses leading digits in its OCR. Both sides of the balance sheet agree on the same incomplete number, so reconciliation alone misses the error. An explicit [rejection list](reports/qa_exclusions.json) excludes those totals without supplying replacement values.

Confidence scores are heuristics, not calibrated probabilities. Some financial labels and notes also admit different interpretations; the chosen capital, cash, depreciation and COGS definitions are documented in the field catalog. The rules and rejection list were developed on this corpus, so performance on unseen filings remains unmeasured.

## What was left out

Additional OCR, model-based extraction and automatic correction of damaged digits were left out to keep the solution reproducible and the evidence auditable. Missing values are not inferred. An independent human evaluation and broader layout testing remain future work.

With another week, the priorities would be:

1. Label a separate evaluation set and measure field accuracy and evidence-box quality.
2. Add targeted OCR retries for damaged rows, measuring the gain against cost and latency.
3. Improve table boundary and comparative-date detection on unseen layouts.
4. Confirm ambiguous financial definitions before expanding derived-field coverage.

## How I used AI

I used Codex for pipeline design and implementation, tests, debugging and documentation. Validation combined automated checks with AI-assisted inspection of the source PDFs. Initial rules selected an N-1 column, merged percentages into amounts and accepted truncated totals; these cases led to regression tests and explicit exclusions. Independent personal verification of the extracted values is still pending. The extraction pipeline itself makes no LLM calls.

## References

- [Official brief](challenges/bilan/BRIEF.md) and [original challenge README](docs/UPSTREAM_README.md)
- [Technical notes](docs/TECHNICAL_NOTES.md)
- [Coverage and measured runtime](reports/summary.md)
- [Validation report](reports/validation_report.json) and [extraction diagnostics](reports/diagnostics.json)

The source corpus and challenge files come from upstream revision `a705bcc86614c8552cc4270c762a6a6399c751ba`.
