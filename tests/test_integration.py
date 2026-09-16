import copy
import hashlib
import json
from pathlib import Path

import pytest

from bilan_pipeline.documents import discover, load
from bilan_pipeline.extraction import extract, unit_evidence
from bilan_pipeline.field_catalog import FIELDS
from bilan_pipeline.geometry import polygon_to_norm
from bilan_pipeline.validation import validate
from tools.bbox_viewer import polygon_to_norm as official_conversion

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def results():
    return json.loads((ROOT / "results.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schema():
    return json.loads(
        (ROOT / "challenges/bilan/schema/results.schema.json").read_text(encoding="utf-8")
    )


def test_discovery_integrity_and_coverage():
    entries = discover(ROOT / "data", ROOT / "challenges/bilan/BRIEF.md")
    assert len(entries) == 15
    assert len({e["doc_id"] for e in entries}) == 15
    assert not any("error" in e for e in entries)
    assert len({e["siren"] for e in entries}) == 5
    inventory = json.loads((ROOT / "reports/inventory.json").read_text(encoding="utf-8"))
    assert sum(d["page_count"] for d in inventory["documents"]) == 415
    assert all(p["ocr_present"] for d in inventory["documents"] for p in d["pages"])


def test_catalog_matches_canonical_schema():
    canonical = json.loads(
        (ROOT / "challenges/bilan/schema/financial_fields.json").read_text(encoding="utf-8")
    )
    assert set(FIELDS) == {f["field_key"] for f in canonical["fields"]}


def test_results_schema_and_semantics(results, schema):
    assert validate(results, schema, ROOT) == []


@pytest.mark.parametrize(
    "mutation", ["duplicate", "unknown", "unit", "page", "bbox", "nan", "string", "formula"]
)
def test_invalid_results_rejected(results, schema, mutation):
    broken = copy.deepcopy(results)
    f = broken["documents"][0]["fields"][0]
    if mutation == "duplicate":
        broken["documents"][0]["fields"].append(copy.deepcopy(f))
    elif mutation == "unknown":
        f["field_key"] = "NOT_A_FINANCIAL_FIELD"
    elif mutation == "unit":
        f["unit"] = "count"
    elif mutation == "page":
        f["page"] = 9999
    elif mutation == "bbox":
        f["bbox"] = [0.8, 0.5, 0.2, 0.5]
    elif mutation == "nan":
        f["value"] = float("nan")
    elif mutation == "string":
        f["value"] = "123"
    elif mutation == "formula":
        f["value"] += 1
    assert validate(broken, schema, ROOT)


def test_official_viewer_geometry_equivalence():
    poly = [[142.3, 346.1], [1270.5, 343.8], [1271.2, 392.7], [141.8, 397.2]]
    assert polygon_to_norm(poly, 598.08, 844.32) == pytest.approx(
        official_conversion(poly, 598.08, 844.32)
    )


def test_null_and_deposit_date_are_rejected(results, schema):
    broken = copy.deepcopy(results)
    broken["documents"][0]["fields"][0]["value"] = None
    assert validate(broken, schema, ROOT)
    broken = copy.deepcopy(results)
    broken["documents"][0]["fiscal_year_end"] = "2023-06-05"
    assert validate(broken, schema, ROOT)


def test_visual_regressions_current_year_and_local_units(results):
    docs = {d["doc_id"]: d for d in results["documents"]}
    # Values read in the PDFs during visual QA, not an external gold dataset.
    expected = [
        ("63e2481c916269756a09542b", "PL_REVENUE_FRGAAP", 4978292),
        ("63e13943526e1f30cd100db5", "BS_TOTAL_ASSETS_FRGAAP", 1807858),
        ("63e8ebbb54febda17c19ee7c", "PL_PERSONNEL_COSTS_FRGAAP", 1609519),
        ("68f0a715f28d8aaf48046416", "BS_CASH_CURRENT_ASSET_FRGAAP", 300456),
        ("66cd893cedec9b09d50191e8", "META_AVG_WORKFORCE_FRGAAP", 0),
    ]
    for did, key, value in expected:
        assert next(f for f in docs[did]["fields"] if f["field_key"] == key)["value"] == value
    assert docs["63e8ebbb54febda17c19ee7d"]["unit_detection"]["unit"] == "EUR"
    assert not any(
        f["field_key"] == "BS_TOTAL_ASSETS_FRGAAP"
        for f in docs["6860f28ca0138eae340c7453"]["fields"]
    )
    assert not any(
        f["field_key"] == "META_AVG_WORKFORCE_FRGAAP"
        for f in docs["63e13943526e1f30cd100db6"]["fields"]
    )


def test_extraction_is_deterministic_and_reads_real_ocr():
    entry = discover(ROOT / "data", ROOT / "challenges/bilan/BRIEF.md")[0]
    pages, _ = load(entry)
    args = (pages, entry["meta"]["dateCloture"], unit_evidence(pages))
    first, _ = extract(*args)
    second, _ = extract(*args)
    assert first == second
    assert len(first) == 4
    assert all(f["evidence_components"][0]["ocr_indices"] for f in first)


def test_output_matches_static_visual_review(results):
    audit = json.loads((ROOT / "reports/visual_audit.json").read_text(encoding="utf-8"))
    records = {d["doc_id"]: d for d in audit["records"]}
    assert set(records) == {d["doc_id"] for d in results["documents"]}
    for doc in results["documents"]:
        evidence = [
            {k: f[k] for k in ["field_key", "value", "unit", "page", "bbox"]} for f in doc["fields"]
        ]
        digest = hashlib.sha256(
            json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        assert digest == records[doc["doc_id"]]["evidence_fingerprint_sha256"], (
            "Changed evidence requires a fresh visual review, not an automatic manifest update."
        )
