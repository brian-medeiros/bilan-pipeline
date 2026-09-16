"""Geometry compatible with the official 300 dpi bounding-box viewer."""

from __future__ import annotations

import math
from collections.abc import Iterable


def polygon_to_norm(polygon: list, width: float, height: float) -> list[float]:
    if width <= 0 or height <= 0 or not polygon:
        raise ValueError("Missing polygon or invalid page dimensions")
    xs, ys = zip(*polygon)
    box = [
        min(xs) / (width * 300 / 72),
        min(ys) / (height * 300 / 72),
        max(xs) / (width * 300 / 72),
        max(ys) / (height * 300 / 72),
    ]
    if any(not math.isfinite(v) or v < -0.001 or v > 1.001 for v in box):
        raise ValueError(f"OCR polygon outside displayed PDF dimensions: {box}")
    box = [min(1.0, max(0.0, v)) for v in box]
    if box[0] >= box[2] or box[1] >= box[3]:
        raise ValueError("Degenerate bounding box")
    return box


def union(boxes: Iterable[list[float]]) -> list[float]:
    boxes = list(boxes)
    if not boxes:
        raise ValueError("Cannot union an empty set of boxes")
    return [
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    ]


def center(box: list[float]) -> tuple[float, float]:
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def same_row(a: list[float], b: list[float], tolerance: float = 0.006) -> bool:
    return abs(center(a)[1] - center(b)[1]) <= max(tolerance, min(a[3] - a[1], b[3] - b[1]) * 0.65)
