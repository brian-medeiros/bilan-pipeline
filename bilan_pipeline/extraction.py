"""Label/code matching with row geometry and explicit current-year columns."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date

from .field_catalog import FIELDS, ROWS, INTERPRETATIONS
from .geometry import center, same_row, union
from .parsing import normalize, parse_number


def classify(lines: list[dict]) -> set[str]:
    text = " ".join(ocr_line["norm"] for ocr_line in lines)
    forms = set()
    if re.search(r"bilan\s*-?\s*actif", text):
        forms.add("ASSETS")
    if re.search(r"bilan\s*-?\s*passi[ftr]", text):
        forms.add("LIABILITIES")
    if re.search(r"compte de r[e]?[sſ][u]?i?ltat|compte de resuitat", text) and re.search(
        r"achats|salaires", text
    ):
        forms.add("PL")
    if re.search(r"compte de r[e]?sultat.*seconde partie|2053\s*20\d\d", text):
        forms.add("PL_CONT")
    if re.search(r"effectif moyen|2058.?c", text):
        forms.add("META")
    # Require title and content, never a form number in a footnote alone.
    return forms


def panels(page: dict) -> list[dict]:
    lines = page["lines"]
    titles = [
        ocr_line
        for ocr_line in lines
        if re.search(r"^bilan\s*-?\s*(?:actif|passif)|^compte de resultat", ocr_line["norm"])
    ]
    split = (
        page["orientation"] in (1, 3)
        and any(center(ocr_line["box"])[0] < 0.5 for ocr_line in titles)
        and any(center(ocr_line["box"])[0] > 0.5 for ocr_line in titles)
    )
    result = []
    for lower, upper in [(0, 0.5), (0.5, 1)] if split else [(0, 1)]:
        selected = []
        for line in lines:
            if lower <= center(line["box"])[0] < upper:
                b = line["box"]
                selected.append(
                    {
                        **line,
                        "box": [
                            (b[0] - lower) / (upper - lower),
                            b[1],
                            (b[2] - lower) / (upper - lower),
                            b[3],
                        ],
                    }
                )
        cells = []
        for cell in page["cells"]:
            b = cell["box"]
            if b[0] >= lower and b[2] <= upper:
                cells.append(
                    {
                        **cell,
                        "box": [
                            (b[0] - lower) / (upper - lower),
                            b[1],
                            (b[2] - lower) / (upper - lower),
                            b[3],
                        ],
                    }
                )
        result.append(
            {
                **page,
                "lines": selected,
                "cells": cells,
                "forms": classify(selected),
                "panel": [lower, upper],
            }
        )
    return result


def unit_evidence(pages: list[dict]) -> dict:
    euros, thousands, local_thousands = [], [], []
    for page in pages:
        page_text = " ".join(ocr_line["norm"] for ocr_line in page["lines"])
        table_scoped = ("filiales" in page_text and "participations" in page_text) or any(
            "tableau" in ocr_line["norm"]
            and re.search(r"milliers|kilo.?[ec]uros|k€", ocr_line["norm"])
            for ocr_line in page["lines"]
        )
        for line in page["lines"]:
            t = line["norm"]
            evidence = {"page": page["page"], "bbox": line["bbox"], "text": line["text"]}
            if re.search(r"milliers|kilo.?[ec]uros|\bkeur\b|k€", t):
                if table_scoped or not re.search(
                    r"exprime|indique|presente|montants|en milliers|en kilo", t
                ):
                    local_thousands.append(
                        {**evidence, "scope": "table" if table_scoped else "inline_amount"}
                    )
                else:
                    thousands.append(evidence)
            elif re.search(r"\beuros?\b|\beur\b", t) and re.search(
                r"bilan|total|annexe|en euros|dossier|compte de res|benefice de l.exercice", t
            ):
                euros.append(evidence)
    if thousands and euros:
        return {
            "unit": None,
            "confidence": 0,
            "reason": "Conflicting document-level unit evidence",
            "evidence": euros + thousands,
            "local_kEUR_tables": local_thousands,
        }
    return {
        "unit": "kEUR" if thousands else ("EUR" if euros else None),
        "confidence": 0.95 if thousands or euros else 0,
        "evidence": thousands or euros,
        "local_kEUR_tables": local_thousands,
        "reason": "Table-scoped kilo-euro notes do not override the main statements.",
    }


def date_in(text: str) -> list[str]:
    found = []
    for d, m, y in re.findall(r"(?<!\d)(\d{2})/(\d{2})/(\d{4}|\d{2})(?!\d)", text):
        try:
            year = int(y) + (2000 if len(y) == 2 and int(y) < 70 else 1900 if len(y) == 2 else 0)
            found.append(date(year, int(m), int(d)).isoformat())
        except ValueError:
            pass
    return found


def columns(panel: dict, form: str, fiscal: str) -> dict | None:
    lines = panel["lines"]
    headers = [
        ocr_line
        for ocr_line in lines
        if 0.04 < center(ocr_line["box"])[1] < 0.36 and center(ocr_line["box"])[0] > 0.4
    ]
    dated = [
        ocr_line
        for ocr_line in headers
        if fiscal in date_in(ocr_line["text"])
        and not ocr_line["norm"].startswith("au ")
        and not re.search(r"exercice clos|periode|edition", ocr_line["norm"])
    ]
    dated += [
        ocr_line
        for ocr_line in headers
        if fiscal in date_in(ocr_line["text"])
        and ocr_line["norm"].startswith("au ")
        and center(ocr_line["box"])[1] > 0.18
    ]
    prior = [
        ocr_line
        for ocr_line in headers
        if any(d < fiscal for d in date_in(ocr_line["text"]))
        and not ocr_line["norm"].startswith("du ")
    ]
    n1 = [
        ocr_line
        for ocr_line in headers
        if re.search(r"(?:exercice|net).*n\s*[-−]\s*1", ocr_line["norm"])
    ]
    current = [
        ocr_line
        for ocr_line in headers
        if re.fullmatch(r"(?:exercice|net)\s*\(?n\)?\s*:?|net", ocr_line["norm"])
    ]
    if form == "PL":
        totals = [
            ocr_line
            for ocr_line in headers
            if ocr_line["norm"] == "total" and center(ocr_line["box"])[1] < 0.2
        ]
        if totals:
            current = totals
    if dated:
        # Table dates lower on the page outrank document-level date stamps.
        current = [max(dated, key=lambda ocr_line: center(ocr_line["box"])[1])]
    if form == "ASSETS":
        nets = sorted(
            [ocr_line for ocr_line in headers if ocr_line["norm"] == "net"],
            key=lambda ocr_line: center(ocr_line["box"])[0],
        )
        if nets:
            current = [nets[0]]
            if len(nets) > 1:
                prior = prior + nets[1:]
    if current:
        anchor = current[0]
        cx, cy = center(anchor["box"])
        if dated and form == "META":
            # Histories can place N-1 on the left of N; never fill a blank N.
            dated_prior = [
                ocr_line
                for ocr_line in prior
                if abs(center(ocr_line["box"])[0] - cx) > 0.045
                and abs(center(ocr_line["box"])[1] - cy) < 0.06
            ]
            if dated_prior:
                nearest = min(
                    dated_prior, key=lambda ocr_line: abs(center(ocr_line["box"])[0] - cx)
                )
                px = center(nearest["box"])[0]
                gap = abs(px - cx)
                return {
                    "current": [cx - gap * 0.48, min(1, cx + gap * 0.55)],
                    "previous": [px - gap * 0.48, px + gap * 0.55],
                    "strategy": "dated_history",
                    "header": {
                        "text": anchor["text"],
                        "bbox": anchor["bbox"],
                        "page": panel["page"],
                    },
                    "previous_date": max(date_in(nearest["text"])),
                }
        nexts = [
            ocr_line
            for ocr_line in prior + n1
            if center(ocr_line["box"])[0] > cx + 0.055
            and abs(center(ocr_line["box"])[1] - cy) < 0.07
        ]
        nx = min((center(ocr_line["box"])[0] for ocr_line in nexts), default=None)
        if nx:
            gap = nx - cx
            lo, hi = cx - gap / 2, (cx + nx) / 2
            prev_bounds = [hi, min(1, nx + gap * 0.7)]
        else:
            lo, hi, prev_bounds = max(0.4, cx - 0.075), min(1, cx + 0.065), None
            if any("dgfip" in ocr_line["norm"] for ocr_line in lines):
                hi = 1.0
        # Percentage columns are independent columns, never thousands fragments.
        percents = [
            center(ocr_line["box"])[0]
            for ocr_line in headers
            if ocr_line["norm"] == "%" and center(ocr_line["box"])[0] > cx
        ]
        if percents:
            hi = min(hi, min(percents) - 0.006)
            if nx:
                p = [x for x in percents if x > nx]
                if p:
                    prev_bounds[1] = min(p) - 0.006
        return {
            "current": [lo, hi],
            "previous": prev_bounds,
            "strategy": "header_geometry",
            "header": {"text": anchor["text"], "bbox": anchor["bbox"], "page": panel["page"]},
            "previous_date": next(
                (d for ocr_line in nexts for d in date_in(ocr_line["text"]) if d < fiscal), None
            ),
        }
    # Damaged Sage table headers: repeated right-aligned numeric columns, with
    # current then comparative in this identified two-year statement family.
    if any("sage" in ocr_line["norm"] or "devise d" in ocr_line["norm"] for ocr_line in lines):
        edges = Counter(
            round(ocr_line["box"][2], 2)
            for ocr_line in lines
            if parse_number(ocr_line["text"]) is not None
            and ocr_line["box"][2] > 0.65
            and 0.2 < center(ocr_line["box"])[1] < 0.85
        )
        peaks = []
        for edge, count in edges.most_common():
            if count >= 5 and all(abs(edge - p) > 0.055 for p in peaks):
                peaks.append(edge)
        peaks.sort()
        if len(peaks) == 2 or (form == "ASSETS" and len(peaks) in (3, 4)):
            a, b = peaks[-2:]
            return {
                "current": [a - (b - a) * 0.85, a + 0.018],
                "previous": [b - (b - a) * 0.85, b + 0.018],
                "strategy": "sage_repeated_columns",
                "previous_date": None,
                "header": None,
            }
    return None


def read_value(panel: dict, anchor: dict, bounds: list[float]) -> dict | None:
    lo, hi = bounds
    row = [
        ocr_line
        for ocr_line in panel["lines"]
        if ocr_line["box"][0] > anchor["box"][2] - 0.01
        and same_row(anchor["box"], ocr_line["box"])
        and ocr_line is not anchor
    ]
    row = sorted(row, key=lambda ocr_line: ocr_line["box"][0])
    tokens = [
        ocr_line for ocr_line in row if re.fullmatch(r"[\d\s.,()+−–-]+", ocr_line["text"].strip())
    ]
    if not tokens:
        return None
    # Refuse nearby footnote labels, separate amounts and multiple cells.
    groups = []
    for token in tokens:
        crosses_boundary = bool(groups) and any(
            center(groups[-1][-1]["box"])[0] < edge < center(token["box"])[0] for edge in (lo, hi)
        )
        if groups and not crosses_boundary and token["box"][0] - groups[-1][-1]["box"][2] < 0.026:
            groups[-1].append(token)
        else:
            groups.append([token])
    groups = [g for g in groups if lo <= center(union(t["box"] for t in g))[0] <= hi]
    if len(groups) != 1:
        return None
    tokens = groups[0]
    raw = " ".join(ocr_line["text"] for ocr_line in tokens)
    corrections = []
    if raw.strip().endswith(")") and "(" not in raw:
        raw = "(" + raw
        corrections.append(
            "Opening parenthesis missing in OCR; closing parenthesis in an isolated numeric cell establishes the printed accounting-negative convention."
        )
    value = parse_number(raw)
    if value is None:
        return None
    box = union(ocr_line["bbox"] for ocr_line in tokens)
    # Cell agreement is supplementary; OCR polygons remain the actual evidence.
    cell_agreement = any(
        c["score"] > 0.7
        and all(
            c["box"][0] - 0.003 <= center(t["box"])[0] <= c["box"][2] + 0.003
            and c["box"][1] - 0.003 <= center(t["box"])[1] <= c["box"][3] + 0.003
            for t in tokens
        )
        and c["box"][2] - c["box"][0] < 0.3
        for c in panel["cells"]
    )
    return {
        "value": value,
        "page": panel["page"],
        "bbox": box,
        "text": raw,
        "ocr_indices": [ocr_line["ocr_index"] for ocr_line in tokens],
        "ocr_score": min(ocr_line["score"] for ocr_line in tokens),
        "label": anchor["text"],
        "label_bbox": anchor["bbox"],
        "corrections": corrections,
        "cell_agreement": cell_agreement,
    }


def extract(
    pages: list[dict], fiscal: str, unit: dict, exclusions: list[dict] | None = None
) -> tuple[list[dict], dict]:
    candidates = {name: [] for name in ROWS}
    diag = {"panels": [], "rejected": [], "omissions": {}, "components": {}}
    for page in pages:
        for panel in panels(page):
            diag["panels"].append(
                {"page": page["page"], "panel": panel["panel"], "forms": sorted(panel["forms"])}
            )
            for name, spec in ROWS.items():
                forms = set(spec.forms) & panel["forms"]
                if not forms:
                    continue
                form = sorted(forms)[0]
                labels = [
                    ocr_line
                    for ocr_line in panel["lines"]
                    if any(re.search(p, ocr_line["norm"]) for p in spec.labels)
                    and ocr_line["box"][3] - ocr_line["box"][1] < 0.06
                ]
                codes = [
                    ocr_line
                    for ocr_line in panel["lines"]
                    if ocr_line["text"].strip().upper() in spec.codes
                ]
                anchors = [
                    (ocr_line, any(same_row(ocr_line["box"], c["box"]) for c in codes))
                    for ocr_line in labels
                ]
                # Codes alone are accepted only inside a classified form.
                anchors.extend(
                    (c, True)
                    for c in codes
                    if not any(same_row(c["box"], ocr_line["box"]) for ocr_line in labels)
                )
                col = columns(panel, form, fiscal)
                for anchor, code in anchors:
                    if name == "workforce":
                        inline = re.search(
                            r"effectif moyen.*?[:. ](\d+(?:[,.]\d+)?)\s*personnes", anchor["norm"]
                        )
                        if inline:
                            evidence = {
                                "value": parse_number(inline[1]),
                                "page": page["page"],
                                "bbox": anchor["bbox"],
                                "text": anchor["text"],
                                "ocr_indices": [anchor["ocr_index"]],
                                "ocr_score": anchor["score"],
                                "label": anchor["text"],
                                "label_bbox": anchor["bbox"],
                                "corrections": [],
                                "cell_agreement": False,
                            }
                            candidates[name].append(
                                {
                                    **evidence,
                                    "confidence": 0.94,
                                    "confidence_factors": {
                                        "inline_label": True,
                                        "ocr": anchor["score"],
                                    },
                                    "column": {"strategy": "explicit_narrative"},
                                    "previous": None,
                                }
                            )
                            continue
                    if not col:
                        diag["rejected"].append(
                            {
                                "component": name,
                                "page": page["page"],
                                "label": anchor["text"],
                                "reason": "No reliable current-year column",
                            }
                        )
                        continue
                    evidence = read_value(panel, anchor, col["current"])
                    if not evidence:
                        diag["rejected"].append(
                            {
                                "component": name,
                                "page": page["page"],
                                "label": anchor["text"],
                                "reason": "Blank, ambiguous or unparseable current-year cell",
                            }
                        )
                        continue
                    if evidence["ocr_score"] < 0.75:
                        diag["rejected"].append(
                            {
                                "component": name,
                                "page": page["page"],
                                "reason": "OCR score below 0.75",
                                "evidence": evidence,
                            }
                        )
                        continue
                    confidence = (
                        0.78
                        + 0.07 * code
                        + 0.06 * evidence["ocr_score"]
                        + 0.03 * evidence["cell_agreement"]
                        + 0.03 * (col["strategy"] == "header_geometry")
                    )
                    if evidence["corrections"]:
                        confidence -= 0.06
                    prev = read_value(panel, anchor, col["previous"]) if col["previous"] else None
                    candidates[name].append(
                        {
                            **evidence,
                            "confidence": round(confidence, 4),
                            "confidence_factors": {
                                "code_match": code,
                                "ocr": evidence["ocr_score"],
                                "cell_agreement": evidence["cell_agreement"],
                                "classified_form": form,
                                "column_strategy": col["strategy"],
                                "unit_confidence": unit["confidence"],
                            },
                            "column": col,
                            "previous": prev,
                        }
                    )
    chosen = {}
    for name, hits in candidates.items():
        for exclusion in exclusions or []:
            if exclusion["component"] == name:
                rejected = [h for h in hits if h["page"] == exclusion["page"]]
                if rejected:
                    diag["rejected"].append(
                        {
                            "component": name,
                            "reason": exclusion["reason"],
                            "policy": "explicit_visual_QA",
                            "candidates": rejected,
                        }
                    )
                hits = [h for h in hits if h["page"] != exclusion["page"]]
        hits.sort(key=lambda h: (-h["confidence"], h["page"]))
        if not hits:
            continue
        # Exact duplicate pages can differ by one currency unit due to printed
        # rounding; all such differences stay visible, never overwritten.
        conflicts = [h for h in hits[1:] if abs(h["value"] - hits[0]["value"]) > 1]
        if conflicts:
            diag["rejected"].append(
                {"component": name, "reason": "Conflicting candidates", "candidates": hits}
            )
            continue
        chosen[name] = dict(hits[0])
        chosen[name]["alternative_candidates"] = [
            {"page": h["page"], "value": h["value"], "bbox": h["bbox"]} for h in hits[1:]
        ]
        if not chosen[name]["previous"]:
            alternatives = [
                h
                for h in hits[1:]
                if h["previous"]
                and h["column"].get("previous_date")
                and h["previous"]["ocr_score"] >= 0.75
            ]
            if alternatives:
                chosen[name]["previous"] = alternatives[0]["previous"]
                chosen[name]["column"] = {
                    **chosen[name]["column"],
                    "previous_date": alternatives[0]["column"]["previous_date"],
                    "comparative_source": "Corroborating alternate statement page; current values agree within one printed unit.",
                }
    diag["components"] = chosen
    fields = []
    for key, names in FIELDS.items():
        missing = [n for n in names if n not in chosen]
        if missing or (unit["unit"] is None and names != ("workforce",)):
            diag["omissions"][key] = (
                "Missing/unsafe components: " + ", ".join(missing)
                if missing
                else "Unresolved monetary unit"
            )
            continue
        pieces = [chosen[n] for n in names]
        if len({p["page"] for p in pieces}) != 1:
            diag["omissions"][key] = (
                "Derived components span different pages; no honest single main region"
            )
            continue
        confidence = min(p["confidence"] for p in pieces)
        if confidence < 0.80:
            diag["omissions"][key] = "Confidence below automatic threshold (0.80)"
            continue
        f = {
            "field_key": key,
            "value": sum(p["value"] for p in pieces),
            "unit": "count" if names == ("workforce",) else unit["unit"],
            "page": pieces[0]["page"],
            "bbox": union(p["bbox"] for p in pieces),
            "snippet": " + ".join(f"{n}: {p['text']}" for n, p in zip(names, pieces)),
            "confidence": confidence,
            "confidence_factors": [p["confidence_factors"] for p in pieces],
            "evidence_components": [{**p, "component": n} for n, p in zip(names, pieces)],
        }
        if len(pieces) > 1:
            f["formula"] = " + ".join(names)
        if key in INTERPRETATIONS:
            f["interpretation"] = INTERPRETATIONS[key]
        fields.append(f)
    return fields, diag


def fiscal_context(pages: list[dict], fiscal: str) -> dict:
    """Preserve observed dates and duration evidence without guessing periods."""
    evidence = []
    for page in pages:
        for line in page["lines"]:
            t = line["norm"]
            if re.search(r"exercice.*(?:duree|clos|clot|mois)|periode du", t):
                nearby = [
                    ocr_line for ocr_line in page["lines"] if same_row(ocr_line["box"], line["box"])
                ]
                text = " ".join(
                    ocr_line["text"]
                    for ocr_line in sorted(nearby, key=lambda ocr_line: ocr_line["box"][0])
                )
                dates = date_in(text)
                duration = re.search(r"duree de (\d+) mois", normalize(text))
                if dates or duration:
                    evidence.append(
                        {
                            "page": page["page"],
                            "bbox": union(ocr_line["bbox"] for ocr_line in nearby),
                            "text": text,
                            "dates": dates,
                            "duration_months": int(duration[1]) if duration else None,
                        }
                    )
    starts = sorted(
        {
            d
            for e in evidence
            if fiscal in e["dates"] and re.search(r"periode du|recouvrant", normalize(e["text"]))
            for d in e["dates"]
            if d < fiscal
        }
    )
    durations = sorted({e["duration_months"] for e in evidence if e["duration_months"] is not None})
    return {
        "fiscal_year_end": fiscal,
        "observed_start_date_candidates": starts,
        "observed_duration_months": durations,
        "exceptional_duration_observed": any(d != 12 for d in durations),
        "evidence": evidence,
    }
