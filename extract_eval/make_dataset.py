"""Generate a labelled set of synthetic CRE loan term sheets.

Three layouts mimic what shows up in practice: a clean key/value sheet, a
lender term sheet with synonyms, dotted leaders and abbreviated numbers, and a
narrative summary. Every document also carries distractor values (fees, appraised
value, prepayment terms) that a naive extractor will grab by mistake.

Usage: python -m extract_eval.make_dataset --n 45 --seed 7
"""
import argparse
import json
import random
from datetime import date
from pathlib import Path

from .pdfgen import write_pdf

NAMES = ["Harbor Point", "Cedar Ridge", "Lakeshore", "Maple Grove", "Riverside", "Summit Park", "Oak Hollow",
         "Bayview", "Granite Falls", "Willow Creek", "Sterling Heights", "Pine Valley", "Copper Mill", "Northgate"]
SUFFIXES = ["Holdings LLC", "Owner LLC", "Partners LP", "Residential LLC", "Investors LLC", "Apartments LP"]
STREETS = ["Main Street", "Oak Avenue", "Market Street", "Lake Drive", "Park Boulevard", "Elm Street", "River Road"]
CITIES = [("Austin", "TX", "787"), ("Phoenix", "AZ", "850"), ("Atlanta", "GA", "303"), ("Denver", "CO", "802"),
          ("Charlotte", "NC", "282"), ("Nashville", "TN", "372"), ("Tampa", "FL", "336"), ("Columbus", "OH", "432")]


def random_record(rng):
    city, state, zip3 = rng.choice(CITIES)
    return {
        "borrower": f"{rng.choice(NAMES)} {rng.choice(SUFFIXES)}",
        "property_address": f"{rng.randint(100, 9999)} {rng.choice(STREETS)}, {city}, {state} {zip3}{rng.randint(10, 99)}",
        "loan_amount": rng.randrange(2_000_000, 80_000_000, 50_000),
        "interest_rate": round(rng.randrange(450, 876, 5) / 100, 2),
        "maturity_date": date(rng.randint(2028, 2036), rng.randint(1, 12), 1).isoformat(),
        "ltv": rng.randrange(100, 151) / 2,  # 50.0 .. 75.0 in 0.5 steps
        "noi": rng.randrange(150_000, 6_000_000, 1_000),
        "units": rng.randint(20, 450),
    }


def _long_date(iso):
    d = date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def _short_date(iso):
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b')} {d.year}"


def _millions(v, style):
    m = v / 1e6
    text = f"{m:.3f}".rstrip("0").rstrip(".")
    return f"USD {text} million" if style == 0 else f"${text}MM"


def _distractors(r, rng):
    appraised = round(r["loan_amount"] / (r["ltv"] / 100), -3)
    return [
        f"Appraised Value: ${appraised:,.0f}",
        f"Origination Fee: {rng.choice(['0.50', '0.75', '1.00'])}% of the loan amount",
        f"Prepayment: {rng.choice(['1.0', '2.0', '3.0'])}% declining, open in final 90 days",
        f"Guarantor: {rng.choice(NAMES)} Capital Partners",
    ]


def layout_key_value(r, rng):
    lines = ["LOAN TERM SHEET", "", f"Borrower: {r['borrower']}", f"Property Address: {r['property_address']}",
             f"Loan Amount: ${r['loan_amount']:,}", f"Interest Rate: {r['interest_rate']:.2f}%",
             f"Maturity Date: {_long_date(r['maturity_date'])}", f"LTV: {r['ltv']:.1f}%",
             f"Net Operating Income: ${r['noi']:,}", f"Units: {r['units']}"]
    return lines + [""] + _distractors(r, rng)


def layout_lender(r, rng):
    def row(label, value):
        return f"{label} {'.' * (34 - len(label))} {value}"
    rate = f"{round(r['interest_rate'] * 100):d} bps" if rng.random() < 0.5 else f"{r['interest_rate']:.2f}% fixed"
    lines = ["INDICATIVE TERMS - SENIOR MORTGAGE FINANCING", "", "Summary of Terms",
             row("Borrower Entity", r["borrower"]), row("Collateral", r["property_address"]),
             row("Facility Amount", _millions(r["loan_amount"], rng.randint(0, 1))), row("Coupon", rate),
             row("Final Maturity", r["maturity_date"]), row("Max LTV", f"{r['ltv']:g}%"),
             row("In-Place NOI", _millions(r["noi"], 1)), row("Unit Count", f"{r['units']} units")]
    return lines + [""] + [row(*d.split(": ", 1)) for d in _distractors(r, rng)]


def layout_narrative(r, rng):
    para = (f"This memo summarizes the proposed financing for {r['borrower']} (the \"Borrower\"), secured by a "
            f"{r['units']}-unit multifamily property located at {r['property_address']}. The Lender proposes a senior "
            f"loan of ${r['loan_amount']:,} bearing interest at a fixed rate of {r['interest_rate']:.2f} percent per "
            f"annum and maturing on {_short_date(r['maturity_date'])}. The loan represents {r['ltv']:g}% of appraised "
            f"value and is sized against in-place net operating income of ${r['noi']:,}.")
    return ["CREDIT MEMO - FINANCING SUMMARY", "", para, ""] + _distractors(r, rng)


LAYOUTS = [layout_key_value, layout_lender, layout_narrative]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=45)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    out = Path(args.out)
    (out / "docs").mkdir(parents=True, exist_ok=True)
    with open(out / "labels.jsonl", "w", encoding="utf-8", newline="
") as f:
        for i in range(args.n):
            record = random_record(rng)
            layout = LAYOUTS[i % len(LAYOUTS)]
            name = f"doc_{i:03d}.pdf"
            write_pdf(out / "docs" / name, layout(record, rng))
            f.write(json.dumps({"doc": name, "layout": layout.__name__, "fields": record}) + "\n")
    print(f"wrote {args.n} documents to {out / 'docs'}")


if __name__ == "__main__":
    main()
