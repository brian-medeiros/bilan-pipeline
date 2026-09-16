import pytest

from bilan_pipeline.documents import upright
from bilan_pipeline.extraction import columns, extract, read_value, unit_evidence
from bilan_pipeline.parsing import normalize


def line(text, x0, y0, x1, y1, index=0):
    b = [x0, y0, x1, y1]
    return {
        "text": text,
        "norm": normalize(text),
        "box": b,
        "bbox": b,
        "score": 0.99,
        "ocr_index": index,
    }


def panel(lines, forms=None):
    return {
        "page": 1,
        "lines": lines,
        "cells": [],
        "orientation": 0,
        "forms": forms or {"PL"},
        "panel": [0, 1],
    }


def test_fragments_join_without_eating_percent_column():
    anchor = line("Salaires et traitements", 0.1, 0.4, 0.4, 0.41)
    p = panel(
        [
            anchor,
            line("1", 0.48, 0.4, 0.49, 0.41),
            line("234", 0.495, 0.4, 0.52, 0.41),
            line("567", 0.525, 0.4, 0.55, 0.41),
            line("32,06", 0.561, 0.4, 0.59, 0.41),
        ]
    )
    evidence = read_value(p, anchor, [0.45, 0.557])
    assert evidence["value"] == 1234567
    assert evidence["bbox"][2] == 0.55


def test_blank_current_cell_does_not_take_comparative():
    anchor = line("Salaires", 0.1, 0.4, 0.4, 0.41)
    p = panel([anchor, line("999", 0.88, 0.4, 0.94, 0.41)])
    assert read_value(p, anchor, [0.65, 0.82]) is None


def test_separate_printed_sign_and_parentheses():
    anchor = line("Resultat financier", 0.1, 0.4, 0.4, 0.41)
    p = panel([anchor, line("-", 0.69, 0.4, 0.70, 0.41), line("123", 0.705, 0.4, 0.76, 0.41)])
    assert read_value(p, anchor, [0.65, 0.8])["value"] == -123
    p["lines"] = [anchor, line("123)", 0.705, 0.4, 0.76, 0.41)]
    value = read_value(p, anchor, [0.65, 0.8])
    assert value["value"] == -123
    assert value["corrections"]


def test_header_selects_net_current_not_gross_or_previous():
    p = panel(
        [
            line("31/12/2023", 0.48, 0.1, 0.68, 0.11),
            line("31/12/2022", 0.84, 0.1, 0.94, 0.11),
            line("Brut", 0.45, 0.13, 0.5, 0.14),
            line("Net", 0.70, 0.13, 0.76, 0.14),
            line("Net", 0.87, 0.13, 0.93, 0.14),
        ]
    )
    col = columns(p, "ASSETS", "2023-12-31")
    assert col["current"][0] < 0.75 < col["current"][1]
    assert not col["current"][0] < 0.90 < col["current"][1]
    assert not col["current"][0] < 0.48 < col["current"][1]


def test_history_with_previous_year_to_left():
    p = panel(
        [line("31/12/2023", 0.88, 0.12, 0.96, 0.14), line("31/12/2022", 0.77, 0.12, 0.85, 0.14)],
        {"META"},
    )
    col = columns(p, "META", "2023-12-31")
    assert col["strategy"] == "dated_history"
    assert col["current"][0] > 0.81
    assert col["previous_date"] == "2022-12-31"


def test_unit_table_and_inline_amount_do_not_override_statement():
    pages = [
        panel([line("Les montants sont exprimes en euros", 0.1, 0.1, 0.9, 0.12)]),
        panel([line("Tableau realise en Kilo-euros", 0.1, 0.1, 0.9, 0.12)]),
        panel([line("Un emprunt de 150 K€", 0.1, 0.1, 0.9, 0.12)]),
    ]
    result = unit_evidence(pages)
    assert result["unit"] == "EUR"
    assert len(result["local_kEUR_tables"]) == 2


def test_document_thousand_euro_unit_and_conflict():
    pages = [panel([line("Montants exprimes en milliers d euros", 0.1, 0.1, 0.9, 0.12)])]
    assert unit_evidence(pages)["unit"] == "kEUR"
    pages.append(panel([line("Bilan en euros", 0.1, 0.1, 0.9, 0.12)]))
    assert unit_evidence(pages)["unit"] is None


def test_derived_requires_all_components_and_preserves_evidence():
    lines = [
        line("Compte de resultat", 0.1, 0.02, 0.7, 0.04),
        line("Total", 0.72, 0.13, 0.76, 0.14),
        line("Exercice N-1", 0.86, 0.13, 0.95, 0.14),
        line("Salaires et traitements", 0.1, 0.40, 0.4, 0.41),
        line("100", 0.71, 0.40, 0.77, 0.41),
        line("Charges sociales", 0.1, 0.45, 0.4, 0.46),
        line("25", 0.72, 0.45, 0.77, 0.46),
    ]
    fields, _ = extract([panel(lines)], "2023-12-31", {"unit": "EUR", "confidence": 0.95})
    personnel = next(f for f in fields if f["field_key"] == "PL_PERSONNEL_COSTS_FRGAAP")
    assert personnel["value"] == 125
    assert len(personnel["evidence_components"]) == 2
    assert personnel["bbox"] == [0.71, 0.40, 0.77, 0.46]
    fields, _ = extract([panel(lines[:-1])], "2023-12-31", {"unit": "EUR", "confidence": 0.95})
    assert not any(f["field_key"] == "PL_PERSONNEL_COSTS_FRGAAP" for f in fields)


def test_rotation_keeps_original_grounding():
    assert upright([0.1, 0.2, 0.3, 0.4], 1) == pytest.approx([0.6, 0.1, 0.8, 0.3])
    assert upright([0.1, 0.2, 0.3, 0.4], 3) == pytest.approx([0.2, 0.7, 0.4, 0.9])
