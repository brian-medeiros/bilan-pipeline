"""Render evidence overlays and upright, labeled contact sheets for review."""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

from .geometry import union


def render(results: Path = Path("results.json"), output: Path = Path("qa")) -> None:
    output.mkdir(exist_ok=True)
    data = json.loads(results.read_text(encoding="utf-8"))
    inventory = {
        d["doc_id"]: d
        for d in json.loads(Path("reports/inventory.json").read_text(encoding="utf-8"))["documents"]
    }
    for doc in data["documents"]:
        tiles = []
        with pymupdf.open(doc["pdf"]) as pdf:
            for f in doc["fields"]:
                page = pdf[f["page"] - 1]
                pix = page.get_pixmap(dpi=130)
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                draw = ImageDraw.Draw(image)
                b = f["bbox"]
                draw.rectangle(
                    [
                        b[0] * image.width,
                        b[1] * image.height,
                        b[2] * image.width,
                        b[3] * image.height,
                    ],
                    outline="red",
                    width=2,
                )
                region = union([b] + [c["label_bbox"] for c in f["evidence_components"]])
                x0, y0, x1, y1 = region
                crop = image.crop(
                    (
                        max(0, int(x0 * image.width) - 8),
                        max(0, int(y0 * image.height) - 10),
                        min(image.width, int(x1 * image.width) + 8),
                        min(image.height, int(y1 * image.height) + 10),
                    )
                )
                orientation = inventory[doc["doc_id"]]["pages"][f["page"] - 1]["ocr_orientation"]
                if orientation:
                    crop = crop.rotate(-90 * orientation, expand=True)
                if crop.width > 1250:
                    crop.thumbnail((1250, 1000))
                tile = Image.new("RGB", (1280, max(65, crop.height + 28)), "white")
                ImageDraw.Draw(tile).text(
                    (6, 4),
                    f"{f['field_key']} = {f['value']} {f['unit']} | PDF page {f['page']}",
                    fill="black",
                )
                tile.paste(crop, (6, 25))
                tiles.append(tile)
            for page_number in sorted({f["page"] for f in doc["fields"]}):
                p = pdf[page_number - 1]
                pix = p.get_pixmap(dpi=100)
                im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                draw = ImageDraw.Draw(im)
                for f in doc["fields"]:
                    if f["page"] == page_number:
                        b = f["bbox"]
                        draw.rectangle(
                            [b[0] * im.width, b[1] * im.height, b[2] * im.width, b[3] * im.height],
                            outline="red",
                            width=2,
                        )
                im.save(output / f"{doc['doc_id']}_page{page_number}.png")
        sheet = Image.new("RGB", (1280, sum(t.height for t in tiles) + 35), "#eeeeee")
        ImageDraw.Draw(sheet).text(
            (6, 8), f"{doc['siren']} | {doc['fiscal_year_end']} | {doc['doc_id']}", fill="black"
        )
        y = 35
        for tile in tiles:
            sheet.paste(tile, (0, y))
            y += tile.height
        sheet.save(output / f"{doc['doc_id']}_review.png")


if __name__ == "__main__":
    render()
