"""HTTP API for the extractor, built to run behind a load balancer on Kubernetes.

POST /v1/extract   multipart PDF upload -> values, evidence, blank fields
GET  /healthz      liveness
GET  /readyz       readiness
GET  /metrics      Prometheus

Security choices:
- API key required (X-API-Key), compared in constant time; keys come from a Kubernetes Secret
- uploads capped (MAX_UPLOAD_MB) and must start with the PDF magic bytes, whatever the filename says
- the upload lives in a private temp file that is always deleted; nothing is persisted
- document contents are never logged, only sizes, timings and field counts
"""
import hmac
import json
import logging
import os
import tempfile
import time
import uuid

from fastapi import FastAPI, File, Header, HTTPException, Query, Request, Response, UploadFile
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from extract_eval.extractors import EXTRACTORS, load_text
from extract_eval.normalize import normalize
from extract_eval.schema import FIELDS

MAX_UPLOAD_BYTES = int(float(os.environ.get("MAX_UPLOAD_MB", "10")) * 1024 * 1024)
API_KEYS = [k.strip() for k in os.environ.get("API_KEYS", "").split(",") if k.strip()]
ALLOWED_EXTRACTORS = ("rules", "hybrid")

REQUESTS = Counter("extraction_requests_total", "Extraction requests", ["extractor", "outcome"])
LATENCY = Histogram("extraction_duration_seconds", "End-to-end extraction time", ["extractor"],
                    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30))
BLANKS = Histogram("extraction_blank_fields", "Fields left blank per document", buckets=tuple(range(0, len(FIELDS) + 1)))

log = logging.getLogger("extraction")
logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI(title="extraction-service", version="0.1.0")


def require_key(key):
    if not API_KEYS:  # fail closed: a misconfigured deployment rejects everything
        raise HTTPException(503, "service has no API keys configured")
    if not key or not any(hmac.compare_digest(key, k) for k in API_KEYS):
        raise HTTPException(401, "invalid or missing API key")


@app.middleware("http")
async def request_id_and_log(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["x-request-id"] = rid
    if request.url.path not in ("/healthz", "/readyz", "/metrics"):
        log.info(json.dumps({"request_id": rid, "method": request.method, "path": request.url.path,
                             "status": response.status_code, "ms": round((time.perf_counter() - start) * 1000, 1)}))
    return response


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz(response: Response):
    if not API_KEYS:
        response.status_code = 503
        return {"ready": False, "reason": "no API keys configured"}
    return {"ready": True}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/extract")
async def extract(file: UploadFile = File(...), extractor: str = Query("rules"),
                  x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    if extractor not in ALLOWED_EXTRACTORS:
        raise HTTPException(400, f"extractor must be one of {ALLOWED_EXTRACTORS}")

    body = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(body) > MAX_UPLOAD_BYTES:
        REQUESTS.labels(extractor, "too_large").inc()
        raise HTTPException(413, f"file larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    if not body.startswith(b"%PDF-"):
        REQUESTS.labels(extractor, "not_pdf").inc()
        raise HTTPException(415, "file is not a PDF")

    start = time.perf_counter()
    fd, path = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(body)
        try:
            text = load_text(path)
        except Exception:
            REQUESTS.labels(extractor, "unreadable").inc()
            raise HTTPException(422, "could not read the PDF")
        ex = EXTRACTORS[extractor]()
        raw = ex.extract(text)
    finally:
        os.remove(path)

    values = {f: (str(v).strip() if FIELDS[f] == "text" and v else normalize(FIELDS[f], v)) for f, v in raw.items()}
    blank = [f for f, v in values.items() if v is None]
    LATENCY.labels(extractor).observe(time.perf_counter() - start)
    BLANKS.observe(len(blank))
    REQUESTS.labels(extractor, "ok").inc()
    return {"values": values,
            "evidence": {f: ex.last_evidence.get(f) for f, v in values.items() if v is not None},
            "blank_fields": blank, "extractor": extractor}
