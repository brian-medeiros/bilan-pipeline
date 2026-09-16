# Technical notes

Detailed extraction rules, evidence handling and validation for the [Bilan pipeline](../README.md). Paths and commands below are relative to the repository root.

## Problem interpretation

The supplied `financial_fields.json` is the contract. Its labels and notes are not completely consistent. The interpretation is explicit in `bilan_pipeline/field_catalog.py` and in affected output fields:

| Field | Operational definition |
|---|---|
| Revenue | Printed net revenue total, including domestic and export sales |
| COGS | Literal French-label sum: FS + FT + FU + FV + FM; every component must be observed |
| Personnel | Wages FY + social charges FZ |
| External services | FW, not the broader Sage subtotal called "TOTAL charges externes" |
| Depreciation | GA, following the English label and explanatory note; provisions excluded |
| Financial result | Printed net financial result, retaining its sign |
| Income tax | HK / impots sur les benefices |
| Assets | Net total assets, never gross assets or depreciation |
| Equity | Total capitaux propres, not situation nette alone |
| Capital | Called-up share capital DA, following the explicit note; reserves/premiums excluded |
| Cash | Disponibilites CF, following the explicit note; VMP is retained separately in diagnostics |
| Workforce | Explicit average workforce; unit `count` |

The COGS definition follows the literal additive label, including the signed production-stock figure. This is a challenge-specific interpretation, not a claim that adding production stock is the universal economic definition of COGS. Capital, cash and depreciation have similarly documented label/note ambiguities. Changing those definitions requires changing the central catalog and rerunning QA.

## Architecture

```text
BRIEF.md -> discovery -> PDF + metadata + OCR -> upright analysis panels
         -> form classification -> year columns -> row/cell association
         -> numeric parsing -> component selection -> derived fields
         -> schema/domain validation -> results.json + reports
```

- `documents.py`: scope discovery, identity checks, PDF hashes, page dimensions, OCR loading and rotation transforms.
- `field_catalog.py`: financial labels, observed OCR variants, form families, codes, formulas and interpretation notes.
- `geometry.py` / `parsing.py`: tested coordinate conversion, unions, row alignment and French number parsing.
- `extraction.py`: page classification, panels, units, columns, components, candidates, confidence and fiscal context.
- `validation.py`: official JSON Schema plus stronger semantic, balance and comparative checks.
- `__main__.py`: CLI, batch error handling, measurement and JSON serialization.
- `qa.py`: reproducible red overlays and upright evidence contact sheets.

## Extraction strategy

Labels and fiscal codes are matched only on compatible statement pages. OCR polygons establish row alignment and column membership. Numeric fragments are joined within a column; percentage columns are explicit boundaries. Table cells provide supplementary agreement when their geometry is plausible. Their contents are not trusted as a replacement for the flat OCR.

Three layout families are handled: fiscal forms, ordinary annual statements and rotated two-panel statements. Damaged Sage headers have a restricted fallback based on repeated numeric-column right edges. This fallback is medium confidence and was visually reviewed. No financial values are hardcoded in the pipeline.

## Document and page discovery

The scope is parsed from the official brief, not copied into a separate filename list. Each PDF must have a real `%PDF-` header and matching registry metadata. All 15 IDs were resolved and have OCR files for every page. **41 pages have zero OCR lines**; they still count in the 415-page denominator. Full inventory and page-level geometry are in `reports/inventory.json`.

Git LFS is not required for this revision: `.gitattributes` marks PDFs as binary, and `git lfs ls-files` is empty. The corpus has other companies and actes; these are never extracted.

Form classification uses titles and characteristic content, not physical PDF page numbers. Some filings contain no income statement. A form number appearing only in a footnote is insufficient evidence.

## OCR and geometry handling

Conversion reproduces `tools/bbox_viewer.py`:

```text
x_normalized = x_pixels / (PDF_display_width_points * 300 / 72)
y_normalized = y_pixels / (PDF_display_height_points * 300 / 72)
```

A polygon becomes its min/max rectangle. Only numerical overflows up to 0.001 are clipped; larger mismatches and degenerate boxes are rejected. PDF display dimensions already reflect PDF rotation. OCR orientation is handled separately for analysis; output boxes remain in the original displayed-page coordinate system. No rotation is applied twice.

Two rotated panels are analyzed independently. Derived fields use the smallest rectangle enclosing all component polygons on the same page. Intervening rows may lie inside that rectangle; the exact component boxes remain available. OCR boxes can be tight around glyphs in skewed scans; they are not invented or silently replaced.

## Current year, N-1 and fiscal dates

`fiscal_year_end` comes from the matching registry metadata's `dateCloture`, with its source path. Deposit dates and filename dates are not used. Observed document dates, period ranges and durations are preserved in `fiscal_context`; missing dates/durations are not manufactured.

Current net, comparative net, France, export, gross and depreciation columns are distinguished. Date headers and `Exercice N` / `Net (N)` signals take precedence over numeric-column patterns. Five-year histories can run left-to-right toward the latest year, so N-1 may be on the left. Blank current-year workforce cells are omitted.

Temporal comparisons require a readable, explicit comparative date that equals another filing's closing date. An agreeing duplicate statement can supply the comparative evidence when the primary tax form has no N-1 column. Missing intervening filings and damaged date headers reduce comparison coverage; they are not filled by assuming “one year earlier.”

## Unit detection: a material finding

**The primary statements extracted from Bernachon (328024377) are in EUR.** This differs from a blanket reading of the brief's warning. The actual documents resolve the apparent conflict:

- 2020 PDF page 5 states that amounts are expressed in euros unless otherwise indicated; its balance total is stated in euros.
- 2021 PDF page 6 makes the same EUR statement. Page 11 says “Tableau realise en Kilo-euros” for the **list of subsidiaries and participations**.
- 2022 PDF page 6 states the main accounts in euros; pages 12 and 33 contain subsidiary tables in kilo-euros.
- Other K-euro mentions describe individual loans or transactions. They do not change the unit of the whole financial statement.

The detector distinguishes statement-wide declarations, table-local declarations and inline amounts. Evidence and scope are retained in `unit_detection`. No company ID or number-magnitude heuristic sets the unit. Conflicting statement-wide declarations cause omission. The current output therefore has EUR monetary values and `count` workforce values; it has **no kEUR main-statement fields**. kEUR behavior is tested with synthetic statements and the real local-unit evidence was visually inspected. No values were multiplied or divided by 1,000 in the output.

## Derived fields and numeric parsing

Personnel uses two observed components. COGS uses five, preserving printed signs. A missing component is never zero. This strict policy leaves only one safely supported COGS result in this run. Supplemental VMP values are available in component diagnostics, without claiming every investment is a cash equivalent.

The parser handles ordinary/nonbreaking spaces, decimal commas, grouped periods, leading signs, parentheses, genuine zeros and joined numeric fragments. Blank cells and dashes are absent. Unrecognized alphabetic digit substitutions are rejected. An isolated closing parenthesis can establish a negative accounting value when the OCR missed the opening parenthesis; this correction is explicitly logged. Components retain raw text, OCR indices, OCR scores, labels and boxes.

## Confidence and failure policy

Confidence is an **uncalibrated heuristic**, not a probability of correctness. The score combines a base of 0.78, code agreement (+0.07), minimum OCR score (up to +0.06), table-cell agreement (+0.03) and header-based column selection (+0.03). Parenthesis recovery subtracts 0.06. Derived confidence is the minimum component score. Unit evidence is a separate prerequisite.

- High: at least 0.90.
- Medium: 0.80 to below 0.90; final submitted instances were visually reviewed.
- Low: below 0.80, omitted. Numeric OCR confidence below 0.75 is rejected independently.
- Conflicting candidates differing by more than one printed unit: omitted. One-unit differences across duplicate rounded statements remain visible as alternatives.

`reports/qa_exclusions.json` is an explicit, isolated **rejection-only** exception list. One rotated Bockel page loses leading digits on black total rows. Both asset and liability totals are rejected. No replacement financial value is supplied. Changing inputs requires revisiting these review decisions.

## Validation strategy

Validation checks the official Draft 2020-12 schema, scope membership, PDF existence, unique documents and keys, SIREN/metadata identity, fiscal closing dates, finite numeric values, allowed fields, pages, units, ordered boxes and component sums/enclosure. Domain checks compare net assets with liabilities plus equity and current filings with explicitly dated N-1 evidence. Findings are reported; values are never rewritten to force agreement.

The final run has **14/14 exact balance reconciliations** and **18/18 temporal comparisons within one printed currency unit** (17 exact and one one-euro difference). These are quality proxies. A development-stage error produced matching but incomplete asset/liability totals, demonstrating why reconciliation alone is insufficient.

## Tests and visual reproduction

```bash
python -m pytest -q
python -m bilan_pipeline.qa
```

The tests cover parsing, geometry, official-viewer parity, numeric association, units, current/N-1 selection, reverse histories, derived values, invalid outputs, discovery and real-document regressions. QA images go to ignored `qa/`; the static audit manifest records exactly which result values/boxes were inspected. It is not automatically refreshed to approve new output.

Official viewer cross-check example:

```bash
python tools/bbox_viewer.py --pdf data/401009741/bilans/pdf/bilan_2025-10-03_68f0a715f28d8aaf48046416.pdf --page 2 --ocr data/401009741/bilans/ocr/68f0a715f28d8aaf48046416 --grep Disponibilit
```

## Results and coverage

| SIREN | Fiscal closing dates | Fields per filing |
|---|---|---|
| 820561470 | 2021-08-31 / 2022-08-31 / 2023-08-31 | 4 / 4 / 4 |
| 328024377 | 2020-06-30 / 2021-06-30 / 2022-06-30 | 9 / 11 / 11 |
| 445070311 | 2020-06-30 / 2022-06-30 / 2023-06-30 | 8 / 8 / 8 |
| 504304205 | 2016-12-31 / 2017-12-31 / 2020-12-31 | 11 / 9 / 5 |
| 401009741 | 2022-04-30 / 2023-04-30 / 2025-04-30 | 11 / 10 / 4 |

| Field | Filings covered / 15 |
|---|---|
| Revenue | 9 |
| COGS | 1 |
| Personnel | 10 |
| External services | 10 |
| Depreciation | 9 |
| Financial result | 8 |
| Income tax | 9 |
| Total assets | 14 |
| Total equity | 12 |
| Share capital | 15 |
| Cash | 15 |
| Average workforce | 5 |

Coverage is 117/180; **63 pairs are omitted (35.0%)**. The denominator includes fields genuinely absent from the shipped filings, so it is not recall against an answer key. Per-field omission reasons are in diagnostics.

## Runtime and cost per page

The authoritative, actually measured values are in `results.json.run` and `reports/summary.md`. The timer uses `time.perf_counter()` and includes discovery, reading, parsing, extraction, fiscal context and structural/domain validation. It excludes dependency installation, corpus download, development, agent interaction, visual inspection and final JSON/report writing. Stage subtotals do not include all orchestration overhead. The 415-page denominator includes covers, annexes and pages with empty OCR.

**Marginal runtime API cost: 0.0 EUR total / 0.0 EUR per page.** Hardware, electricity, storage, upstream OCR and the development assistant are not priced. This is not a claim of zero total economic cost.

## Quality assessment methodology

There is no public ground truth and no claimed benchmark accuracy. During development, the agent inspected rendered red-box evidence for all 15 filings, all emitted field types, every derived result, the lower-confidence cases, PDF-rotation and OCR-rotation examples, ordinary/fiscal layouts, and real EUR/kEUR scope statements. The final review manifest covers all 117 emitted fields.

This is an **AI-assisted visual audit, not an independent human audit**. It was also used to improve the rules, so its confirmation rate is not an unbiased precision estimate. Printed digits and grounding were checked; semantic ambiguities remain documented. Some scans have tight OCR boxes. Confidence scores and consistency rates must not be presented as calibrated accuracy.

The regression set contains actual values confirmed in those PDFs. It protects against known failures; it does not demonstrate generalization to unseen companies.

## Known limitations

- Missing income statements explain much of the low coverage for Pautet and the latest Creamande filing.
- COGS omissions are deliberately conservative: absent printed components are not assumed zero.
- Sage equity subtotals and damaged financial-result labels are omitted when the required total cannot be established safely.
- Some comparative dates are unreadable; no temporal score is claimed for those pairs. Company-level comparison coverage is reported.
- Bernachon duplicate presentations sometimes differ by one printed euro; alternatives remain traceable.
- Repeated-column heuristics are specific to the observed layout family. They require fresh QA on new layouts.
- The visual rejection list is corpus-specific and must not be mistaken for general OCR error detection.
- Capital/cash/depreciation/COGS definitions require confirmation if this is extended into a production financial ontology.
