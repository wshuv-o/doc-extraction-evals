"""LLM extractor behaviour, tested offline with a scripted fake client."""
import json
from types import SimpleNamespace

from extract_eval.extractors import HybridExtractor, LLMExtractor

DOC = ("This memo summarizes the proposed financing for Oak Owner LLC, secured by a 120-unit property. "
       "The Lender proposes a senior loan of $12,500,000 at 6.25 percent. Appraised Value: $19,000,000.")


class FakeClient:
    """Returns queued JSON answers and records which fields each call asked for."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.prompts = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.prompts.append(kwargs["messages"][0]["content"])
        content = json.dumps(self.answers.pop(0))
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_hallucinated_evidence_is_retried_then_dropped():
    first = {"loan_amount": {"value": 12_500_000, "evidence": "$12,500,000"},
             "units": {"value": 150, "evidence": "150 units"}}          # not in the document
    retry = {"units": {"value": 150, "evidence": "150 units"}}          # still not grounded
    llm = LLMExtractor(client=FakeClient(first, retry))
    out = llm.extract(DOC, ["loan_amount", "units"])
    assert out == {"loan_amount": 12_500_000, "units": None}
    assert llm.calls == 2


def test_evidence_must_support_the_value():
    # evidence exists in the text but is the appraised value, not the loan amount
    answer = {"loan_amount": {"value": 12_500_000, "evidence": "$19,000,000"}}
    llm = LLMExtractor(client=FakeClient(answer, answer))
    assert llm.extract(DOC, ["loan_amount"]) == {"loan_amount": None}


def test_retry_recovers_field():
    first = {"units": None}
    retry = {"units": {"value": 120, "evidence": "120-unit"}}
    llm = LLMExtractor(client=FakeClient(first, retry))
    assert llm.extract(DOC, ["units"]) == {"units": 120}


def test_hybrid_skips_llm_when_rules_succeed():
    fake = FakeClient()
    hybrid = HybridExtractor(llm=LLMExtractor(client=fake))
    text = "\n".join(["Borrower: Oak Owner LLC", "Property Address: 1 Main Street, Austin, TX 78701",
                      "Loan Amount: $1,000,000", "Interest Rate: 6.00%", "Maturity Date: March 1, 2031",
                      "LTV: 60.0%", "Net Operating Income: $90,000", "Units: 12"])
    hybrid.extract(text)
    assert fake.prompts == []
