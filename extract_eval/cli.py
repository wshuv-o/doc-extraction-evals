"""Run an extractor over the labelled set, write a report, and gate on accuracy.

python -m extract_eval.cli --extractor rules --min-accuracy 0.6 --baseline results/baseline_rules.json
Exit code 1 if accuracy is below --min-accuracy or any field regressed vs the baseline.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from .extractors import EXTRACTORS, load_text
from .scoring import regressions, score


def run(extractor, data_dir):
    rows = []
    with open(Path(data_dir) / "labels.jsonl", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            text = load_text(Path(data_dir) / "docs" / item["doc"])
            rows.append({"doc": item["doc"], "layout": item["layout"], "expected": item["fields"],
                         "predicted": extractor.extract(text)})
    return rows


def to_markdown(name, summary, elapsed):
    lines = [f"## Extractor: `{name}`", "",
             f"**Field accuracy: {summary['accuracy']:.1%}** over {summary['fields_scored']} fields "
             f"({summary['wrong_not_blank']} wrong values, rest left blank) in {elapsed:.1f}s", "",
             "| Field | Accuracy |", "|---|---|"]
    lines += [f"| {f} | {a:.1%} |" for f, a in summary["per_field"].items()]
    lines += ["", "| Layout | Accuracy |", "|---|---|"]
    lines += [f"| {l} | {a:.1%} |" for l, a in summary["per_layout"].items()]
    if summary["failures"]:
        lines += ["", "<details><summary>First failures</summary>", "", "| Doc | Field | Expected | Got |", "|---|---|---|---|"]
        lines += [f"| {x['doc']} | {x['field']} | {x['expected']} | {x['predicted']} |" for x in summary["failures"][:20]]
        lines += ["", "</details>"]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extractor", choices=EXTRACTORS, default="rules")
    ap.add_argument("--data", default="data")
    ap.add_argument("--out-dir", default="results")
    ap.add_argument("--min-accuracy", type=float, default=0.0)
    ap.add_argument("--baseline", help="previous results JSON to compare per-field accuracy against")
    ap.add_argument("--max-drop", type=float, default=0.02, help="allowed per-field accuracy drop vs baseline")
    args = ap.parse_args()

    extractor = EXTRACTORS[args.extractor]()
    start = time.time()
    summary = score(run(extractor, args.data))
    elapsed = time.time() - start

    out = Path(args.out_dir)
    out.mkdir(exist_ok=True)
    (out / f"{extractor.name}.json").write_text(json.dumps(summary, indent=2))
    report = to_markdown(extractor.name, summary, elapsed)
    (out / f"{extractor.name}.md").write_text(report, encoding="utf-8")
    print(report)

    failed = False
    if summary["accuracy"] < args.min_accuracy:
        print(f"FAIL: accuracy {summary['accuracy']:.1%} < required {args.min_accuracy:.1%}")
        failed = True
    if args.baseline and Path(args.baseline).exists():
        for field, (before, after) in regressions(summary, json.loads(Path(args.baseline).read_text()), args.max_drop).items():
            print(f"FAIL: {field} regressed {before:.1%} -> {after:.1%}")
            failed = True
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
