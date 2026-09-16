"""CLI: python -m bilan_pipeline --data-dir data --output results.json."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter

from .documents import discover, load
from .extraction import extract, unit_evidence, fiscal_context
from .validation import domain_report, validate
from .reporting import write_summary


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("results.json"))
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    parser.add_argument("--doc-id")
    parser.add_argument(
        "--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO"
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format="%(levelname)s %(message)s")
    root = Path(__file__).resolve().parent.parent
    schema = json.loads(
        (root / "challenges/bilan/schema/results.schema.json").read_text(encoding="utf-8")
    )
    if args.validate_only:
        errors = validate(json.loads(args.output.read_text(encoding="utf-8")), schema, root)
        for error in errors:
            logging.error(error)
        logging.info("Validation: %d errors", len(errors))
        return int(bool(errors))
    started = perf_counter()
    exclusions = json.loads((root / "reports/qa_exclusions.json").read_text(encoding="utf-8"))[
        "exclusions"
    ]
    entries = discover(args.data_dir, root / "challenges/bilan/BRIEF.md")
    if args.doc_id:
        entries = [e for e in entries if e.get("doc_id") == args.doc_id]
        if not entries:
            parser.error("doc-id is outside the official scope")
    documents, inventory, diagnostics, failures = [], [], {}, []
    stages = Counter()
    for entry in entries:
        try:
            if "error" in entry:
                raise ValueError(entry["error"])
            t = perf_counter()
            pages, inv = load(entry)
            stages["load_seconds"] += perf_counter() - t
            inventory.append(inv)
            t = perf_counter()
            unit = unit_evidence(pages)
            fiscal = entry["meta"]["dateCloture"]
            fields, diag = extract(
                pages, fiscal, unit, [e for e in exclusions if e["doc_id"] == entry["doc_id"]]
            )
            stages["extract_seconds"] += perf_counter() - t
            doc = {
                "pdf": Path(os.path.relpath(entry["pdf_path"].resolve(), root)).as_posix(),
                "siren": entry["siren"],
                "doc_id": entry["doc_id"],
                "fiscal_year_end": fiscal,
                "fiscal_date_source": {
                    "path": Path(os.path.relpath(entry["meta_path"].resolve(), root)).as_posix(),
                    "key": "dateCloture",
                },
                "fiscal_context": fiscal_context(pages, fiscal),
                "unit_detection": unit,
                "fields": fields,
            }
            documents.append(doc)
            diagnostics[entry["doc_id"]] = diag
            logging.info(
                "%s %s: %d fields, %d pages, unit=%s",
                entry["siren"],
                fiscal,
                len(fields),
                len(pages),
                unit["unit"],
            )
        except Exception as exc:
            logging.exception("Document failed: %s", entry["pdf_path"])
            failures.append({"pdf": str(entry["pdf_path"]), "reason": str(exc)})
    count = sum(i["page_count"] for i in inventory)
    result = {
        "documents": documents,
        "run": {
            "cost_eur_per_page": 0.0,
            "cost_total_eur": 0.0,
            "seconds_per_page": 0.0,
            "pages_processed": count,
            "model": "provided OCR + deterministic local rules",
            "notes": "Measured with perf_counter: discovery, PDF/OCR loading, extraction, structural and domain validation. Excludes installation, download, manual/visual QA and final report serialization. Zero marginal API cost; hardware, storage and upstream OCR cost are not estimated. Field content is deterministic; measured timings vary.",
        },
    }
    t = perf_counter()
    errors = validate(result, schema, root)
    report = domain_report(documents, diagnostics)
    stages["validation_seconds"] = perf_counter() - t
    elapsed = perf_counter() - started
    result["run"].update(
        total_seconds=elapsed, seconds_per_page=elapsed / count if count else 0, stages=dict(stages)
    )
    coverage = Counter(f["field_key"] for d in documents for f in d["fields"])
    report.update(
        expected_documents=len(entries),
        processed_documents=len(documents),
        pages_processed=count,
        fields_emitted=sum(coverage.values()),
        coverage_by_field=dict(coverage),
        coverage_by_document={d["doc_id"]: len(d["fields"]) for d in documents},
        structural_errors=errors,
        document_failures=failures,
        run=result["run"],
    )
    write_json(args.output, result)
    write_json(args.reports_dir / "inventory.json", {"documents": inventory})
    write_json(args.reports_dir / "diagnostics.json", diagnostics)
    write_json(args.reports_dir / "validation_report.json", report)
    write_summary(args.reports_dir / "summary.md", report, documents)
    logging.info(
        "Emitted %d fields across %d documents; %.4f seconds/page; %d errors",
        sum(coverage.values()),
        len(documents),
        result["run"]["seconds_per_page"],
        len(errors),
    )
    return int(bool(errors or failures))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as exc:
        logging.error("Cannot complete run: %s", exc)
        sys.exit(2)
