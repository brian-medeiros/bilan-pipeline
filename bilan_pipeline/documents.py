"""Brief-driven discovery and immutable OCR/PDF loading."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pymupdf

from .geometry import polygon_to_norm
from .parsing import normalize


def discover(data_dir: Path, brief: Path) -> list[dict]:
    scope = re.findall(
        r"\| `(\d{9})` \| [^|]+ \| `(bilan_[^`]+\.pdf)`", brief.read_text(encoding="utf-8")
    )
    if len(scope) != 15 or len(set(scope)) != 15:
        raise ValueError("Expected 15 unique PDF entries in the official brief")
    found = []
    for siren, filename in scope:
        base = data_dir / siren / "bilans"
        pdf = base / "pdf" / filename
        meta_path = base / "meta" / Path(filename).with_suffix(".json")
        entry = {"siren": siren, "pdf_path": pdf, "meta_path": meta_path}
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta["siren"] != siren or not filename.endswith(meta["id"] + ".pdf"):
                raise ValueError("Metadata identity does not match PDF")
            if not pdf.read_bytes().startswith(b"%PDF-"):
                raise ValueError("Missing PDF header or unresolved LFS pointer")
            entry.update(meta=meta, doc_id=meta["id"], ocr_dir=base / "ocr" / meta["id"])
        except (OSError, ValueError, KeyError) as exc:
            entry["error"] = str(exc)
        found.append(entry)
    return found


def upright(box: list[float], orientation: int) -> list[float]:
    x0, y0, x1, y1 = box
    if orientation == 1:
        return [1 - y1, x0, 1 - y0, x1]
    if orientation == 2:
        return [1 - x1, 1 - y1, 1 - x0, 1 - y0]
    if orientation == 3:
        return [y0, 1 - x1, y1, 1 - x0]
    return box[:]


def load(entry: dict) -> tuple[list[dict], dict]:
    pages = []
    inventory = {
        "doc_id": entry["doc_id"],
        "siren": entry["siren"],
        "pdf_sha256": hashlib.sha256(entry["pdf_path"].read_bytes()).hexdigest(),
        "pages": [],
    }
    with pymupdf.open(entry["pdf_path"]) as pdf:
        for number, page in enumerate(pdf, 1):
            path = entry["ocr_dir"] / f"page_{number:03}.json"
            raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            if raw and raw.get("page") != number:
                raise ValueError(f"OCR page mismatch: {path}")
            orientation = raw.get("most_frequent_angle", 0)
            lines, rejected = [], []
            for idx, line in enumerate(raw.get("ocr", [])):
                try:
                    original = polygon_to_norm(line["polygon"], page.rect.width, page.rect.height)
                    lines.append(
                        {
                            "text": line["text"],
                            "norm": normalize(line["text"]),
                            "box": upright(original, orientation),
                            "bbox": original,
                            "score": line.get("score", 0),
                            "ocr_index": idx,
                        }
                    )
                except (ValueError, KeyError) as exc:
                    rejected.append({"ocr_index": idx, "reason": str(exc)})
            cells = []
            for region in raw.get("layout", []):
                for cell in region.get("cells", []):
                    b = cell["bbox"]
                    try:
                        b = polygon_to_norm(
                            [[b[0], b[1]], [b[2], b[3]]], page.rect.width, page.rect.height
                        )
                        cells.append(
                            {"box": upright(b, orientation), "score": cell.get("score", 0)}
                        )
                    except ValueError:
                        pass
            pages.append(
                {"page": number, "lines": lines, "cells": cells, "orientation": orientation}
            )
            inventory["pages"].append(
                {
                    "page": number,
                    "width_pt": page.rect.width,
                    "height_pt": page.rect.height,
                    "pdf_rotation": page.rotation,
                    "ocr_orientation": orientation,
                    "skew_angle": raw.get("skew_angle"),
                    "ocr_present": bool(raw),
                    "ocr_lines": len(raw.get("ocr", [])),
                    "layout_regions": len(raw.get("layout", [])),
                    "cells": len(cells),
                    "invalid_polygons": rejected,
                }
            )
    inventory["page_count"] = len(pages)
    return pages, inventory
