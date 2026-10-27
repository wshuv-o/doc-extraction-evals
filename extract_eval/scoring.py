"""Field-level scoring against the labelled set."""
from collections import defaultdict

from .normalize import normalize
from .schema import FIELDS

PERCENT_TOLERANCE = 0.001


def field_correct(field, predicted, expected):
    ftype = FIELDS[field]
    p, e = normalize(ftype, predicted), normalize(ftype, expected)
    if p is None:
        return False
    if ftype == "percent":
        return abs(p - e) <= PERCENT_TOLERANCE
    return p == e


def score(rows):
    """rows: [{"doc", "layout", "expected": {...}, "predicted": {...}}] -> summary dict."""
    per_field = defaultdict(lambda: [0, 0])
    per_layout = defaultdict(lambda: [0, 0])
    missing = 0
    failures = []
    for row in rows:
        for field in FIELDS:
            ok = field_correct(field, row["predicted"].get(field), row["expected"][field])
            for bucket in (per_field[field], per_layout[row["layout"]]):
                bucket[0] += ok
                bucket[1] += 1
            if not ok:
                if row["predicted"].get(field) is None:
                    missing += 1
                failures.append({"doc": row["doc"], "field": field,
                                 "expected": row["expected"][field], "predicted": row["predicted"].get(field)})
    total_ok = sum(v[0] for v in per_field.values())
    total = sum(v[1] for v in per_field.values())
    return {
        "accuracy": round(total_ok / total, 4) if total else 0.0,
        "fields_scored": total,
        # wrong answers are worse than blanks in production: a blank goes to a human, a wrong value doesn't
        "wrong_not_blank": len(failures) - missing,
        "per_field": {f: round(ok / n, 4) for f, (ok, n) in per_field.items()},
        "per_layout": {l: round(ok / n, 4) for l, (ok, n) in per_layout.items()},
        "failures": failures,
    }


def regressions(current, baseline, max_drop):
    """Fields whose accuracy fell more than max_drop below the stored baseline."""
    return {
        f: (baseline["per_field"][f], acc)
        for f, acc in current["per_field"].items()
        if f in baseline.get("per_field", {}) and baseline["per_field"][f] - acc > max_drop
    }
