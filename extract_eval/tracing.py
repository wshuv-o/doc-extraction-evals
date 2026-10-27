"""OpenTelemetry tracing for extraction runs.

Spans: one `extract_document` per document, with child spans for the rules pass and for
every model call (model name, fields requested, token usage, whether it was a retry).

Export targets, picked by environment:
- OTEL_EXPORTER_OTLP_ENDPOINT set and the OTLP exporter installed -> any OTel backend
  (Jaeger, Grafana Tempo, Langfuse, Honeycomb, ...)
- configure(trace_file=...) -> one JSON object per finished span, for offline analysis
- neither -> spans are created but not exported (zero cost in tests)
"""
import json
import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExporter, SpanExportResult

tracer = trace.get_tracer("extract_eval")
_configured = False


class JsonlSpanExporter(SpanExporter):
    def __init__(self, path):
        self.path = path

    def export(self, spans):
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            for s in spans:
                f.write(json.dumps({
                    "name": s.name,
                    "trace_id": format(s.context.trace_id, "032x"),
                    "span_id": format(s.context.span_id, "016x"),
                    "parent_id": format(s.parent.span_id, "016x") if s.parent else None,
                    "duration_ms": round((s.end_time - s.start_time) / 1e6, 2),
                    "attributes": dict(s.attributes or {}),
                    "status": s.status.status_code.name,
                }) + "\n")
        return SpanExportResult.SUCCESS


def configure(trace_file=None, service_name="doc-extraction-evals"):
    """Install a tracer provider once per process."""
    global _configured
    if _configured:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    if trace_file:
        open(trace_file, "w").close()
        provider.add_span_processor(SimpleSpanProcessor(JsonlSpanExporter(trace_file)))
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        except ImportError:
            print("OTEL_EXPORTER_OTLP_ENDPOINT is set but opentelemetry-exporter-otlp is not installed")
    trace.set_tracer_provider(provider)
    _configured = True
