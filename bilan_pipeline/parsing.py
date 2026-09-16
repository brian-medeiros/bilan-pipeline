"""Conservative French numeric parsing; blank cells never become zero."""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation


def normalize(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        "".join(
            c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c)
        ),
    ).strip()


def parse_number(text: str) -> int | float | None:
    raw = text.strip().replace("−", "-").replace("–", "-")
    raw = re.sub(r"(?:€|EUR)$", "", raw, flags=re.I).strip()
    if not raw or raw in {"-", "—", ".", "N/A"}:
        return None
    negative = raw.startswith("(") and raw.endswith(")")
    if negative:
        raw = raw[1:-1].strip()
    raw = re.sub(r"\s+", "", raw)
    if not re.fullmatch(r"[+-]?\d[\d.,]*", raw):
        return None
    if "," in raw:
        # French decimal comma; periods, when also present, group thousands.
        if raw.count(",") != 1:
            return None
        raw = raw.replace(".", "").replace(",", ".")
    elif "." in raw:
        if re.fullmatch(r"[+-]?\d{1,3}(?:\.\d{3})+", raw):
            raw = raw.replace(".", "")
        elif raw.count(".") > 1:
            return None
    try:
        number = Decimal(raw) * (-1 if negative else 1)
    except InvalidOperation:
        return None
    return int(number) if number == number.to_integral_value() else float(number)
