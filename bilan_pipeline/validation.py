"""Schema, geometry, domain and temporal quality proxies (not accuracy)."""

from __future__ import annotations

import math
import json
import re
from datetime import date
from pathlib import Path

import jsonschema
import pymupdf

from .field_catalog import FIELDS


def validate(result: dict, schema: dict, root: Path) -> list[str]:
    errors = [e.message for e in jsonschema.Draft202012Validator(schema).iter_errors(result)]
    if errors:
        return errors
    seen = set()
    expected_names = set(
        re.findall(
            r"`(bilan_[^`]+\.pdf)`",
            (root / "challenges/bilan/BRIEF.md").read_text(encoding="utf-8"),
        )
    )
    for doc in result["documents"]:
        if doc["pdf"] in seen:
            errors.append("Duplicate PDF: " + doc["pdf"])
        seen.add(doc["pdf"])
        if doc.get("fiscal_year_end"):
            try:
                date.fromisoformat(doc["fiscal_year_end"])
            except ValueError:
                errors.append("Invalid fiscal date")
        path = root / doc["pdf"]
        if path.name not in expected_names:
            errors.append("PDF outside the official challenge scope: " + doc["pdf"])
        if not path.is_file():
            errors.append("Missing PDF: " + doc["pdf"])
            continue
        with pymupdf.open(path) as pdf:
            pages = len(pdf)
        meta_path = path.parent.parent / "meta" / path.with_suffix(".json").name
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        if metadata["siren"] != doc["siren"] or metadata["dateCloture"] != doc.get(
            "fiscal_year_end"
        ):
            errors.append("Metadata identity or fiscal closing date mismatch: " + doc["pdf"])
        keys = set()
        units = {f["unit"] for f in doc["fields"] if f["unit"] != "count"}
        if len(units) > 1:
            errors.append("Inconsistent monetary units within document: " + doc["pdf"])
        for f in doc["fields"]:
            k = f["field_key"]
            if k not in FIELDS or k in keys:
                errors.append("Unknown/duplicate field: " + k)
            keys.add(k)
            if (
                not isinstance(f["value"], (int, float))
                or isinstance(f["value"], bool)
                or not math.isfinite(f["value"])
            ):
                errors.append("Nonfinite/non-numeric value: " + k)
                continue
            if (f["unit"] == "count") != (k == "META_AVG_WORKFORCE_FRGAAP"):
                errors.append("Invalid monetary/count unit: " + k)
            b = f["bbox"]
            if (
                len(b) != 4
                or not all(math.isfinite(v) and 0 <= v <= 1 for v in b)
                or b[0] >= b[2]
                or b[1] >= b[3]
            ):
                errors.append("Invalid bounding box: " + k)
            if not 1 <= f["page"] <= pages:
                errors.append("Invalid page: " + k)
            pieces = f.get("evidence_components", [])
            if pieces and abs(sum(p["value"] for p in pieces) - f["value"]) > 1e-8:
                errors.append("Invalid formula: " + k)
            for p in pieces:
                if (
                    p["page"] != f["page"]
                    or any(p["bbox"][i] < b[i] - 1e-9 for i in [0, 1])
                    or any(p["bbox"][i] > b[i] + 1e-9 for i in [2, 3])
                ):
                    errors.append("Component not enclosed: " + k)
    return errors


def domain_report(documents: list[dict], diagnostics: dict) -> dict:
    balance, temporal, outliers = [], [], []
    for doc in documents:
        components = diagnostics.get(doc["doc_id"], {}).get("components", {})
        if "assets" in components and "liabilities" in components:
            a, b = components["assets"]["value"], components["liabilities"]["value"]
            balance.append(
                {
                    "doc_id": doc["doc_id"],
                    "assets": a,
                    "liabilities_plus_equity": b,
                    "difference": a - b,
                    "within_one_printed_unit": abs(a - b) <= 1,
                }
            )
    for newer in documents:
        candidates = [
            d
            for d in documents
            if d["siren"] == newer["siren"]
            and d.get("fiscal_year_end")
            and newer.get("fiscal_year_end")
            and d["fiscal_year_end"] < newer["fiscal_year_end"]
        ]
        for older in candidates:
            old_fields = {f["field_key"]: f for f in older["fields"]}
            for f in newer["fields"]:
                prev = [p.get("previous") for p in f["evidence_components"]]
                if not all(prev) or f["field_key"] not in old_fields:
                    continue
                dates = {p["column"].get("previous_date") for p in f["evidence_components"]}
                # Without an explicit comparative date, don't assume the prior
                # filing is the preceding exercise (late/missing filings exist).
                if dates != {older["fiscal_year_end"]}:
                    continue
                old = old_fields[f["field_key"]]
                v = sum(p["value"] for p in prev)
                factor = 1000 if f["unit"] == "kEUR" else 1
                old_factor = 1000 if old["unit"] == "kEUR" else 1
                difference = v * factor - old["value"] * old_factor
                temporal.append(
                    {
                        "older": older["doc_id"],
                        "newer": newer["doc_id"],
                        "field_key": f["field_key"],
                        "comparative_date": older["fiscal_year_end"],
                        "older_value": old["value"],
                        "newer_comparative_value": v,
                        "difference_in_base_unit": difference,
                        "within_rounding_tolerance": abs(difference) <= max(factor, old_factor),
                        "note": "Units converted only for validation, never for emitted values.",
                    }
                )
                if old["value"] and abs(v * factor / (old["value"] * old_factor)) > 10:
                    outliers.append(temporal[-1])
    coverage = []
    for siren in sorted({d["siren"] for d in documents}):
        ids = {d["doc_id"] for d in documents if d["siren"] == siren}
        checks = [t for t in temporal if t["newer"] in ids]
        coverage.append(
            {
                "siren": siren,
                "filings_considered": len(ids),
                "comparisons_with_explicit_dates": len(checks),
                "reason_for_unchecked_pairs": "Only explicitly dated comparative cells are compared. Missing intervening fiscal years, missing N-1 columns, blank cells and unreadable date headers are not inferred.",
            }
        )
    return {
        "balance_reconciliation": balance,
        "temporal_comparisons": temporal,
        "temporal_coverage": coverage,
        "order_of_magnitude_flags": outliers,
        "note": "These are consistency proxies, not measured extraction accuracy. Rounding differences and real disagreements are retained.",
    }
