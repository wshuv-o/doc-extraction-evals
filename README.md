# doc-extraction-evals

An evaluation harness for LLM document extraction. You can't improve extraction quality if you only eyeball outputs, so this repo measures it: a labelled document set, field-level scoring, and a CI gate that blocks changes that make extraction worse.

It is a public, synthetic version of the approach I use in production at work. That system extracts deal data from bank and real estate documents and writes it into analysts' Excel models. The real documents are confidential, so this repo generates realistic stand-ins.

## What's here

| Part | What it does |
|---|---|
| `make_dataset.py` | Generates 45 labelled CRE loan term sheets as real PDFs in 3 layouts: a key/value sheet, a lender term sheet (synonyms, dotted leaders, `$12.5MM`, `625 bps`), and a narrative credit memo. Every document includes **distractors** (appraised value, fees, prepayment terms) that a naive extractor grabs by mistake. |
| `normalize.py` | One canonical form per type, so `USD 12.5 million`, `$12.5MM` and `$12,500,000` score as the same value. |
| `extractors.py` | **rules**: label-synonym regex baseline. **llm**: model extraction where each value must quote **evidence found verbatim in the document** that actually supports the value; ungrounded fields are retried once, then left blank rather than guessed. **hybrid**: rules first, LLM only for the fields rules missed. |
| `scoring.py` | Field accuracy per field and per layout. Counts **wrong values separately from blanks**: a blank goes to a human, a wrong value silently corrupts a model. |
| `cli.py` + CI | Writes JSON and Markdown reports. Fails the build if accuracy drops below a floor or **any field regresses** vs the stored baseline. |

## Results

Rules baseline (`results/rules.md`):

| Layout | Accuracy |
|---|---|
| key/value sheet | 100% |
| lender term sheet | 100% |
| narrative memo | 0% |
| **Overall** | **66.7%** (0 wrong values, all failures are blanks) |

The baseline never returns a wrong value. It only leaves fields blank, which is the right failure mode. The narrative layout is where an LLM is needed, and `hybrid` calls the model **only for those documents**. That is a third of the documents rather than all of them, which cuts cost and latency.

Run the LLM versions yourself (any OpenAI-compatible endpoint):

```bash
export OPENAI_API_KEY=...            # optionally OPENAI_BASE_URL and EXTRACT_MODEL
python -m extract_eval.cli --extractor hybrid --min-accuracy 0.95
```

## Quick start

```bash
pip install -r requirements.txt
python -m extract_eval.make_dataset --n 45 --seed 7
pytest -q
python -m extract_eval.cli --extractor rules --min-accuracy 0.6 --baseline results/baseline_rules.json
```

## Design decisions

- **Grounding over trust.** The model must return the exact text it read the value from. If that text isn't in the document, or doesn't parse to the claimed value (for example it quoted the appraised value as the loan amount), the field is rejected. Tests cover hallucinated evidence, mismatched evidence and retry recovery, using a fake client so they run offline.
- **Blank beats wrong.** Downstream users can fill a blank. A plausible wrong number in a financial model is the expensive failure, so the report tracks it separately.
- **Per-field regression gate.** Overall accuracy can stay flat while one field collapses. The gate compares every field against the baseline.
- **Deterministic data.** The dataset is seeded, and CI checks that it regenerates identically, so score changes come from code changes, not data drift.

## Next steps

- Scanned-page variants (render to image and add OCR noise) to measure the OCR path.
- LLM-as-judge for free-text fields such as addresses, with a written rubric.
- Cost and latency per document in the report.
