import asyncio
import json

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from mcp.server.mcpserver.exceptions import ToolError

from extract_eval import mcp_server
from extract_eval.extractors import RulesExtractor
from extract_eval.pdfgen import write_pdf
from extract_eval.tracing import JsonlSpanExporter


@pytest.fixture
def docs_root(tmp_path, monkeypatch):
    write_pdf(tmp_path / "sheet.pdf", ["Borrower: Oak Owner LLC", "Loan Amount: $12.5MM", "Units: 120"])
    (tmp_path / "notes.txt").write_text("not a pdf")
    monkeypatch.setattr(mcp_server, "DOCS_ROOT", tmp_path.resolve())
    return tmp_path


def test_server_exposes_three_read_only_tools():
    names = {t.name for t in asyncio.run(mcp_server.server.list_tools())}
    assert names == {"list_fields", "extract_document", "evaluate_extractor"}


def test_extract_document_returns_values_evidence_and_blanks(docs_root):
    out = mcp_server.extract_document("sheet.pdf")
    assert out["values"]["loan_amount"] == 12_500_000
    assert out["evidence"]["loan_amount"] == "Loan Amount: $12.5MM"
    assert out["values"]["borrower"] == "Oak Owner LLC"
    assert "maturity_date" in out["blank_fields"]


@pytest.mark.parametrize("bad", ["../outside.pdf", "notes.txt", "missing.pdf"])
def test_paths_outside_root_or_non_pdf_are_rejected(docs_root, bad):
    with pytest.raises(ToolError):
        mcp_server.extract_document(bad)


def test_unknown_extractor_rejected(docs_root):
    with pytest.raises(ToolError):
        mcp_server.extract_document("sheet.pdf", extractor="llm-without-grounding")


def test_spans_export_as_jsonl(tmp_path):
    path = tmp_path / "spans.jsonl"
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(JsonlSpanExporter(path)))
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("extract_document") as span:
        span.set_attribute("doc", "a.pdf")
        with tracer.start_as_current_span("rules.extract"):
            RulesExtractor().extract("Units: 3")
    spans = [json.loads(line) for line in path.read_text().splitlines()]
    parent = next(s for s in spans if s["name"] == "extract_document")
    child = next(s for s in spans if s["name"] == "rules.extract")
    assert child["parent_id"] == parent["span_id"] and parent["attributes"]["doc"] == "a.pdf"
