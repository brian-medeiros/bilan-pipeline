"""Compact generated report; measured values are never editorial estimates."""

from pathlib import Path

from .field_catalog import FIELDS


def write_summary(path: Path, report: dict, documents: list[dict]) -> None:
    run = report["run"]
    balances = report["balance_reconciliation"]
    temporal = report["temporal_comparisons"]
    total = 12 * report["expected_documents"]
    lines = [
        "# Bilan execution summary",
        "",
        f"- Processed documents: {report['processed_documents']}/{report['expected_documents']}",
        f"- PDF/OCR pages processed: {report['pages_processed']}",
        f"- Emitted fields: {report['fields_emitted']}/{total} ({report['fields_emitted'] / total:.1%})",
        f"- Structural/schema errors: {len(report['structural_errors'])}",
        f"- Batch failures: {len(report['document_failures'])}",
        f"- Measured elapsed time: {run['total_seconds']:.6f} seconds",
        f"- Measured time/page: {run['seconds_per_page']:.8f} seconds",
        f"- Marginal API cost/page: {run['cost_eur_per_page']:.1f} EUR",
        "",
        run["notes"],
        "",
        "## Consistency proxies",
        "",
        f"- Balance reconciliations within one printed unit: {sum(x['within_one_printed_unit'] for x in balances)}/{len(balances)}",
        f"- Temporal checks within one printed unit: {sum(x['within_rounding_tolerance'] for x in temporal)}/{len(temporal)}",
        f"- Exact temporal matches: {sum(x['difference_in_base_unit'] == 0 for x in temporal)}/{len(temporal)}",
        "",
        "These are consistency checks, not an accuracy estimate. See visual_audit.json for the static AI-assisted review record.",
        "",
        "## Coverage by field",
        "",
        "| Field | Emitted filings |",
        "|---|---:|",
    ]
    for key in FIELDS:
        lines.append(f"| {key} | {report['coverage_by_field'].get(key, 0)} |")
    lines += [
        "",
        "## Coverage by document",
        "",
        "| SIREN | Closing date | Document ID | Fields |",
        "|---|---|---|---:|",
    ]
    for doc in documents:
        lines.append(
            f"| {doc['siren']} | {doc['fiscal_year_end']} | {doc['doc_id']} | {len(doc['fields'])} |"
        )
    lines += [
        "",
        "## Temporal coverage",
        "",
        "| SIREN | Filings considered | Explicit-date comparisons |",
        "|---|---:|---:|",
    ]
    for item in report["temporal_coverage"]:
        lines.append(
            f"| {item['siren']} | {item['filings_considered']} | {item['comparisons_with_explicit_dates']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
