import pytest
from fastapi.testclient import TestClient

import service.app as svc
from extract_eval.pdfgen import write_pdf

KEY = "test-key-123"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(svc, "API_KEYS", [KEY])
    return TestClient(svc.app)


@pytest.fixture
def pdf_bytes(tmp_path):
    p = tmp_path / "doc.pdf"
    write_pdf(p, ["Borrower: Oak Owner LLC", "Loan Amount: $12.5MM", "Units: 120"])
    return p.read_bytes()


def post(client, data, key=KEY, **params):
    headers = {"X-API-Key": key} if key else {}
    return client.post("/v1/extract", files={"file": ("doc.pdf", data, "application/pdf")}, headers=headers, params=params)


def test_extracts_values_with_evidence(client, pdf_bytes):
    r = post(client, pdf_bytes)
    assert r.status_code == 200
    body = r.json()
    assert body["values"]["loan_amount"] == 12_500_000
    assert body["values"]["borrower"] == "Oak Owner LLC"
    assert body["evidence"]["units"] == "Units: 120"
    assert "maturity_date" in body["blank_fields"]
    assert r.headers["x-request-id"]


@pytest.mark.parametrize("key", [None, "wrong-key"])
def test_requires_valid_api_key(client, pdf_bytes, key):
    assert post(client, pdf_bytes, key=key).status_code == 401


def test_fails_closed_without_configured_keys(monkeypatch, pdf_bytes):
    monkeypatch.setattr(svc, "API_KEYS", [])
    c = TestClient(svc.app)
    assert post(c, pdf_bytes, key="anything").status_code == 503
    assert c.get("/readyz").status_code == 503


def test_rejects_non_pdf_even_with_pdf_filename(client):
    assert post(client, b"<html>not a pdf</html>").status_code == 415


def test_rejects_oversized_upload(client, monkeypatch):
    monkeypatch.setattr(svc, "MAX_UPLOAD_BYTES", 1024)
    assert post(client, b"%PDF-" + b"0" * 2000).status_code == 413


def test_rejects_corrupt_pdf(client):
    assert post(client, b"%PDF-1.4 garbage").status_code == 422


def test_rejects_unknown_extractor(client, pdf_bytes):
    assert post(client, pdf_bytes, extractor="llm").status_code == 400


def test_metrics_and_probes(client, pdf_bytes):
    post(client, pdf_bytes)
    text = client.get("/metrics").text
    assert 'extraction_requests_total{extractor="rules",outcome="ok"}' in text
    assert client.get("/healthz").status_code == 200 and client.get("/readyz").status_code == 200
