"""Extractors under test. Each takes document text and returns {field: raw value or None}."""
import json
import os
import re

import pdfplumber

from .normalize import normalize
from .schema import DESCRIPTIONS, FIELDS
from .tracing import tracer


def load_text(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


class RulesExtractor:
    """Label-synonym regex baseline. Fast, free, and blind to narrative text."""

    name = "rules"

    SYNONYMS = {
        "borrower": ["borrower entity", "borrower"],
        "property_address": ["property address", "collateral", "address"],
        "loan_amount": ["loan amount", "facility amount", "principal amount"],
        "interest_rate": ["interest rate", "coupon", "rate"],
        "maturity_date": ["maturity date", "final maturity", "maturity"],
        "ltv": ["max ltv", "ltv", "loan-to-value"],
        "noi": ["net operating income", "in-place noi", "noi"],
        "units": ["unit count", "units"],
    }

    def __init__(self):
        self.last_evidence = {}

    def extract(self, text):
        out, self.last_evidence = {}, {}
        with tracer.start_as_current_span("rules.extract") as span:
            for field, labels in self.SYNONYMS.items():
                out[field] = None
                for label in labels:
                    m = re.search(rf"^\s*{re.escape(label)}\s*(?::|\.{{3,}})\s*(.+?)\s*$", text, re.I | re.M)
                    if m:
                        out[field] = m.group(1)
                        self.last_evidence[field] = m.group(0).strip()
                        break
            span.set_attribute("fields_found", sum(v is not None for v in out.values()))
        return out


class LLMExtractor:
    """LLM extraction with grounding: every value must quote evidence found verbatim in the document.

    Fields whose evidence is missing from the text, or doesn't parse to the claimed value,
    are retried once with a focused prompt; anything still ungrounded is returned as None
    rather than guessed. Works with any OpenAI-compatible endpoint (OPENAI_BASE_URL).
    """

    name = "llm"

    def __init__(self, model=None, client=None):
        if client is None:
            from openai import OpenAI
            client = OpenAI()
        self.client = client
        self.model = model or os.environ.get("EXTRACT_MODEL", "gpt-4o-mini")
        self.calls = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self.last_evidence = {}

    def _ask(self, text, fields, retry=False):
        spec = "\n".join(f'- "{f}" ({FIELDS[f]}): {DESCRIPTIONS[f]}' for f in fields)
        prompt = (
            "Extract these fields from the loan document below. For each field return an object "
            '{"value": ..., "evidence": "<exact substring copied from the document>"} or null if absent. '
            "Ignore fees, appraised value and prepayment terms; they are not the requested fields.\n\n"
            f"Fields:\n{spec}\n\nReturn only a JSON object keyed by field name.\n\nDOCUMENT:\n{text}"
        )
        self.calls += 1
        with tracer.start_as_current_span("llm.call") as span:
            span.set_attributes({"llm.model": self.model, "llm.fields_requested": len(fields), "llm.retry": retry})
            resp = self.client.chat.completions.create(
                model=self.model, temperature=0, response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
            )
            usage = getattr(resp, "usage", None)
            if usage is not None:
                self.tokens_in += usage.prompt_tokens or 0
                self.tokens_out += usage.completion_tokens or 0
                span.set_attributes({"llm.tokens_in": usage.prompt_tokens or 0,
                                     "llm.tokens_out": usage.completion_tokens or 0})
            return json.loads(resp.choices[0].message.content)

    @staticmethod
    def _grounded(text, field, item):
        if not isinstance(item, dict) or item.get("value") is None or not item.get("evidence"):
            return False
        flat = lambda s: re.sub(r"\s+", " ", s).lower()
        if flat(item["evidence"]) not in flat(text):
            return False
        # the evidence must support the value, not just exist somewhere in the document
        claimed = normalize(FIELDS[field], item["value"])
        return claimed is not None and (
            normalize(FIELDS[field], item["evidence"]) == claimed
            or flat(str(item["value"])) in flat(item["evidence"])
        )

    def extract(self, text, fields=None):
        fields = list(fields or FIELDS)
        answer = self._ask(text, fields)
        failed = [f for f in fields if not self._grounded(text, f, answer.get(f))]
        if failed:
            retry = self._ask(text, failed, retry=True)
            answer.update({f: retry.get(f) for f in failed})
        grounded = {f for f in fields if self._grounded(text, f, answer.get(f))}
        self.last_evidence = {f: answer[f]["evidence"] for f in grounded}
        return {f: (answer[f]["value"] if f in grounded else None) for f in fields}


class HybridExtractor:
    """Rules first; the LLM is only called for the fields rules could not parse.

    On structured layouts this costs zero model calls, which matters at production volume.
    """

    name = "hybrid"

    def __init__(self, llm=None):
        self.rules = RulesExtractor()
        self.llm = llm or LLMExtractor()
        self.last_evidence = {}

    def extract(self, text):
        out = self.rules.extract(text)
        evidence = dict(self.rules.last_evidence)
        missing = [f for f, v in out.items() if normalize(FIELDS[f], v) is None]
        if missing:
            out.update(self.llm.extract(text, missing))
            evidence.update(self.llm.last_evidence)
        self.last_evidence = evidence
        return out


EXTRACTORS = {"rules": RulesExtractor, "llm": LLMExtractor, "hybrid": HybridExtractor}
