# Bilan: grounded extraction of French annual accounts

## 1. Overview

A local, deterministic pipeline processes the **15 PDFs / 415 pages** listed in the official Bilan brief. It emits **117 of 180 possible document-field pairs (65.0%)**, with normalized evidence boxes, printed units, component provenance and measured runtime. All 12 field types are represented. Unavailable or unsafe fields are omitted.

No credentials, external inference model, new OCR engine or API calls are required at runtime. The original PDFs, OCR, schemas and viewer are unchanged. The upstream README is preserved in `docs/UPSTREAM_README.md`; upstream revision: `a705bcc86614c8552cc4270c762a6a6399c751ba`.

## 2. Problem interpretation

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

## 3. Architecture

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

## 4. Extraction strategy

Labels and fiscal codes are matched only on compatible statement pages. OCR polygons establish row alignment and column membership. Numeric fragments are joined within a column; percentage columns are explicit boundaries. Table cells provide supplementary agreement when their geometry is plausible. Their contents are not trusted as a replacement for the flat OCR.

Three layout families are handled: fiscal forms, ordinary annual statements and rotated two-panel statements. Damaged Sage headers have a restricted fallback based on repeated numeric-column right edges. This fallback is medium confidence and was visually reviewed. No financial values are hardcoded in the pipeline.

## 5. Document and page discovery

The scope is parsed from the official brief, not copied into a separate filename list. Each PDF must have a real `%PDF-` header and matching registry metadata. All 15 IDs were resolved and have OCR files for every page. **41 pages have zero OCR lines**; they still count in the 415-page denominator. Full inventory and page-level geometry are in `reports/inventory.json`.

Git LFS is not required for this revision: `.gitattributes` marks PDFs as binary, and `git lfs ls-files` is empty. The corpus has other companies and actes; these are never extracted.

Form classification uses titles and characteristic content, not physical PDF page numbers. Some filings contain no income statement. A form number appearing only in a footnote is insufficient evidence.

## 6. OCR and geometry handling

Conversion reproduces `tools/bbox_viewer.py`:

```text
x_normalized = x_pixels / (PDF_display_width_points * 300 / 72)
y_normalized = y_pixels / (PDF_display_height_points * 300 / 72)
```

A polygon becomes its min/max rectangle. Only numerical overflows up to 0.001 are clipped; larger mismatches and degenerate boxes are rejected. PDF display dimensions already reflect PDF rotation. OCR orientation is handled separately for analysis; output boxes remain in the original displayed-page coordinate system. No rotation is applied twice.

Two rotated panels are analyzed independently. Derived fields use the smallest rectangle enclosing all component polygons on the same page. Intervening rows may lie inside that rectangle; the exact component boxes remain available. OCR boxes can be tight around glyphs in skewed scans; they are not invented or silently replaced.

## 7. Current year, N-1 and fiscal dates

`fiscal_year_end` comes from the matching registry metadata's `dateCloture`, with its source path. Deposit dates and filename dates are not used. Observed document dates, period ranges and durations are preserved in `fiscal_context`; missing dates/durations are not manufactured.

Current net, comparative net, France, export, gross and depreciation columns are distinguished. Date headers and `Exercice N` / `Net (N)` signals take precedence over numeric-column patterns. Five-year histories can run left-to-right toward the latest year, so N-1 may be on the left. Blank current-year workforce cells are omitted.

Temporal comparisons require a readable, explicit comparative date that equals another filing's closing date. An agreeing duplicate statement can supply the comparative evidence when the primary tax form has no N-1 column. Missing intervening filings and damaged date headers reduce comparison coverage; they are not filled by assuming “one year earlier.”

## 8. Unit detection: a material finding

**The primary statements extracted from Bernachon (328024377) are in EUR.** This differs from a blanket reading of the brief's warning. The actual documents resolve the apparent conflict:

- 2020 PDF page 5 states that amounts are expressed in euros unless otherwise indicated; its balance total is stated in euros.
- 2021 PDF page 6 makes the same EUR statement. Page 11 says “Tableau realise en Kilo-euros” for the **list of subsidiaries and participations**.
- 2022 PDF page 6 states the main accounts in euros; pages 12 and 33 contain subsidiary tables in kilo-euros.
- Other K-euro mentions describe individual loans or transactions. They do not change the unit of the whole financial statement.

The detector distinguishes statement-wide declarations, table-local declarations and inline amounts. Evidence and scope are retained in `unit_detection`. No company ID or number-magnitude heuristic sets the unit. Conflicting statement-wide declarations cause omission. The current output therefore has EUR monetary values and `count` workforce values; it has **no kEUR main-statement fields**. kEUR behavior is tested with synthetic statements and the real local-unit evidence was visually inspected. No values were multiplied or divided by 1,000 in the output.

## 9. Derived fields and numeric parsing

Personnel uses two observed components. COGS uses five, preserving printed signs. A missing component is never zero. This strict policy leaves only one safely supported COGS result in this run. Supplemental VMP values are available in component diagnostics, without claiming every investment is a cash equivalent.

The parser handles ordinary/nonbreaking spaces, decimal commas, grouped periods, leading signs, parentheses, genuine zeros and joined numeric fragments. Blank cells and dashes are absent. Unrecognized alphabetic digit substitutions are rejected. An isolated closing parenthesis can establish a negative accounting value when the OCR missed the opening parenthesis; this correction is explicitly logged. Components retain raw text, OCR indices, OCR scores, labels and boxes.

## 10. Confidence and failure policy

Confidence is an **uncalibrated heuristic**, not a probability of correctness. The score combines a base of 0.78, code agreement (+0.07), minimum OCR score (up to +0.06), table-cell agreement (+0.03) and header-based column selection (+0.03). Parenthesis recovery subtracts 0.06. Derived confidence is the minimum component score. Unit evidence is a separate prerequisite.

- High: at least 0.90.
- Medium: 0.80 to below 0.90; final submitted instances were visually reviewed.
- Low: below 0.80, omitted. Numeric OCR confidence below 0.75 is rejected independently.
- Conflicting candidates differing by more than one printed unit: omitted. One-unit differences across duplicate rounded statements remain visible as alternatives.

`reports/qa_exclusions.json` is an explicit, isolated **rejection-only** exception list. One rotated Bockel page loses leading digits on black total rows. Both asset and liability totals are rejected. No replacement financial value is supplied. Changing inputs requires revisiting these review decisions.

## 11. Validation strategy

Validation checks the official Draft 2020-12 schema, scope membership, PDF existence, unique documents and keys, SIREN/metadata identity, fiscal closing dates, finite numeric values, allowed fields, pages, units, ordered boxes and component sums/enclosure. Domain checks compare net assets with liabilities plus equity and current filings with explicitly dated N-1 evidence. Findings are reported; values are never rewritten to force agreement.

The final run has **14/14 exact balance reconciliations** and **18/18 temporal comparisons within one printed currency unit** (17 exact and one one-euro difference). These are quality proxies. A development-stage error produced matching but incomplete asset/liability totals, demonstrating why reconciliation alone is insufficient.

## 12. Installation

Use Python 3.11 or newer from the repository root:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Linux/macOS instead: source .venv/bin/activate
python -m pip install -r requirements.txt
```

No `.env` is needed. `.env.example` documents the absence of application environment variables and credentials. Optional development tooling: `python -m pip install -e ".[dev]"`. The project is intended to run from this complete clone, which contains its official schemas and data.

## 13. Running

```bash
python -m bilan_pipeline --data-dir data --output results.json
```

Single-document debugging without overwriting the full report:

```bash
python -m bilan_pipeline --doc-id 63e881158be6eb9f9d1ff975 --output tmp/one.json --reports-dir tmp/one-reports --log-level DEBUG
```

Extraction is deterministic. Timings vary by machine and filesystem cache. The batch continues after a document failure and exits nonzero if any document or structural validation fails. A successful partial `--doc-id` run is allowed. Data paths are serialized relative to the repository root.

## 14. Validating output

```bash
python -m bilan_pipeline --validate-only --output results.json
```

This validates structure and semantics without rerunning extraction. Domain and timing reports are refreshed by a full extraction. Review `reports/validation_report.json`, `reports/diagnostics.json` and the compact `reports/summary.md`.

## 15. Tests and visual reproduction

```bash
python -m pytest -q
python -m bilan_pipeline.qa
```

The tests cover parsing, geometry, official-viewer parity, numeric association, units, current/N-1 selection, reverse histories, derived values, invalid outputs, discovery and real-document regressions. QA images go to ignored `qa/`; the static audit manifest records exactly which result values/boxes were inspected. It is not automatically refreshed to approve new output.

Official viewer cross-check example:

```bash
python tools/bbox_viewer.py --pdf data/401009741/bilans/pdf/bilan_2025-10-03_68f0a715f28d8aaf48046416.pdf --page 2 --ocr data/401009741/bilans/ocr/68f0a715f28d8aaf48046416 --grep Disponibilit
```

## 16. Results and coverage

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

## 17. Runtime and cost per page

The authoritative, actually measured values are in `results.json.run` and `reports/summary.md`. The timer uses `time.perf_counter()` and includes discovery, reading, parsing, extraction, fiscal context and structural/domain validation. It excludes dependency installation, corpus download, development, agent interaction, visual inspection and final JSON/report writing. Stage subtotals do not include all orchestration overhead. The 415-page denominator includes covers, annexes and pages with empty OCR.

**Marginal runtime API cost: 0.0 EUR total / 0.0 EUR per page.** Hardware, electricity, storage, upstream OCR and the development assistant are not priced. This is not a claim of zero total economic cost.

## 18. Quality assessment methodology

There is no public ground truth and no claimed benchmark accuracy. During development, the agent inspected rendered red-box evidence for all 15 filings, all emitted field types, every derived result, the lower-confidence cases, PDF-rotation and OCR-rotation examples, ordinary/fiscal layouts, and real EUR/kEUR scope statements. The final review manifest covers all 117 emitted fields.

This is an **AI-assisted visual audit, not an independent human audit**. It was also used to improve the rules, so its confirmation rate is not an unbiased precision estimate. Printed digits and grounding were checked; semantic ambiguities remain documented. Some scans have tight OCR boxes. Confidence scores and consistency rates must not be presented as calibrated accuracy.

The regression set contains actual values confirmed in those PDFs. It protects against known failures; it does not demonstrate generalization to unseen companies.

## 19. Known limitations

- Missing income statements explain much of the low coverage for Pautet and the latest Creamande filing.
- COGS omissions are deliberately conservative: absent printed components are not assumed zero.
- Sage equity subtotals and damaged financial-result labels are omitted when the required total cannot be established safely.
- Some comparative dates are unreadable; no temporal score is claimed for those pairs. Company-level comparison coverage is reported.
- Bernachon duplicate presentations sometimes differ by one printed euro; alternatives remain traceable.
- Repeated-column heuristics are specific to the observed layout family. They require fresh QA on new layouts.
- The visual rejection list is corpus-specific and must not be mistaken for general OCR error detection.
- Capital/cash/depreciation/COGS definitions require confirmation if this is extended into a production financial ontology.

## 20. Intentionally left undone and trade-off

No external model, custom OCR training, paid API, speculative blank filling or document-specific financial-value patching was added. No push, PR or reviewer invitation was performed.

Local rules make **cost and latency low**, execution reproducible and provenance straightforward. Conservative omissions sacrifice **coverage** to reduce unsupported claims. They do not guarantee perfect precision. Supporting multiple observed layouts improves **generalization**, but this small reviewed corpus is insufficient to prove it. Rich component evidence and explicit exceptions prioritize **traceability** over compact output.

## 21. With one additional week

1. Obtain independent human annotations for a held-out set, including semantic definitions.
2. Add targeted OCR rereads for black total rows, blank OCR cells and damaged headers; measure incremental cost and accuracy.
3. Infer grid boundaries more robustly and validate row-code sequences to reduce layout-specific heuristics.
4. Expand explicit comparative-date recovery and financial subtotal checks while retaining restatements.
5. Resolve the schema label/note ambiguities with Takeovers, then rerun all derived-field audits.

## 22. How I used AI

A Codex agent inspected the repository, designed and implemented the pipeline, wrote tests, reviewed code and generated documentation. The same agent inspected rendered PDF evidence using image tools. No independent human verification has yet been performed by the repository owner.

Financial values were never accepted solely from an AI suggestion: the runtime reads the shipped OCR and associates it with PDF geometry. Unit scope, printed signs, current-year columns and problematic totals were checked against rendered source pages rather than delegated to unchecked language-model guesses. The agent initially proposed rules that selected a prior-year column, joined percentage values to amounts, and accepted truncated black-row totals. Those mistakes were identified in visual QA and corrected or explicitly excluded. An initial historical workforce candidate was also removed because the current-year cell was blank. These corrections are represented by regression tests and the rejection manifest.

## Local submission steps (not executed)

Create an empty repository in your own GitHub account. Preserve the upstream snapshot as the base branch and submit the solution as a PR **to your repository**, not to Takeovers:

```bash
git remote rename origin upstream
git remote add origin https://github.com/YOUR_ACCOUNT/YOUR_REPOSITORY.git
git branch main upstream/main
git push -u origin main
git add README.md docs .gitignore .env.example requirements.txt pyproject.toml bilan_pipeline tests reports results.json
git commit -m "Implement grounded local Bilan extraction pipeline"
git push -u origin codex/bilan-solution
gh pr create --repo YOUR_ACCOUNT/YOUR_REPOSITORY --base main --head codex/bilan-solution --title "Bilan: local grounded extraction" --body-file docs/PR_DESCRIPTION.md
gh pr edit --repo YOUR_ACCOUNT/YOUR_REPOSITORY --add-reviewer YassineBouderbala --add-reviewer AleBastos25
```

If GitHub requires collaborator access for those reviewers, invite them through repository settings first. Review the changes and audit limitations before submitting. Do not add `.env`, caches or QA renders.
