"""Turn the many ways a value can be written into one canonical form.

Both the ground truth and every extractor's output go through these functions,
so "$12.5MM", "USD 12.5 million" and "$12,500,000" all score as the same value.
"""
import re
from datetime import date, datetime

_MULTIPLIERS = {"k": 1e3, "thousand": 1e3, "m": 1e6, "mm": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9, "billion": 1e9}


def parse_money(raw):
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return round(float(raw))
    s = str(raw).lower().replace("usd", "").replace("$", "").replace(",", "").strip()
    m = re.match(r"^(-?\d+(?:\.\d+)?)\s*([a-z]+)?", s)
    if not m:
        return None
    value = float(m.group(1))
    suffix = m.group(2)
    if suffix:
        if suffix not in _MULTIPLIERS:
            return None
        value *= _MULTIPLIERS[suffix]
    return round(value)


def parse_percent(raw):
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return round(float(raw), 4)
    s = str(raw).lower().strip()
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(%|percent|bps|basis points)?", s)
    if not m:
        return None
    value = float(m.group(1))
    if m.group(2) in ("bps", "basis points"):
        value /= 100
    return round(value, 4)


_DATE_FORMATS = ["%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d %b %Y", "%d %B %Y", "%m/%d/%Y"]


def parse_date(raw):
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw.isoformat()
    s = re.sub(r"\s+", " ", str(raw).strip().rstrip("."))
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_int(raw):
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    m = re.search(r"\d[\d,]*", str(raw))
    return int(m.group(0).replace(",", "")) if m else None


def parse_text(raw):
    if raw is None:
        return None
    s = re.sub(r"\s+", " ", str(raw)).strip().strip(".,;").lower()
    return s or None


PARSERS = {"money": parse_money, "percent": parse_percent, "date": parse_date, "int": parse_int, "text": parse_text}


def normalize(field_type, raw):
    try:
        return PARSERS[field_type](raw)
    except (ValueError, TypeError):
        return None
