"""MCP server that lets an agent (Claude Desktop, Claude Code, Cursor, ...) use the extractor.

Tools:
- list_fields: the schema the extractor fills
- extract_document: fields + the exact evidence each value came from, and which fields are blank
- evaluate_extractor: run the labelled eval set and return accuracy, so an agent can check
  quality before trusting a change

Run (stdio):  python -m extract_eval.mcp_server
Write access is deliberately absent: the server reads documents and reports; it never edits files.
"""
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .cli import cost_summary, run
from .extractors import EXTRACTORS, load_text
from .normalize import normalize
from .schema import DESCRIPTIONS, FIELDS
from .scoring import score

server = MCPServer("doc-extraction")

# Documents may only be read from this directory, so a prompt-injected path can't read arbitrary files.
DOCS_ROOT = Path(os.environ.get("EXTRACT_DOCS_ROOT", "data")).resolve()


def _resolve(path: str) -> Path:
    p = (DOCS_ROOT / path).resolve()
    if DOCS_ROOT not in p.parents and p != DOCS_ROOT:
        raise ToolError(f"path must be inside {DOCS_ROOT}")
    if not p.is_file() or p.suffix.lower() != ".pdf":
        raise ToolError(f"not a PDF file: {path}")
    return p


@server.tool()
def list_fields() -> dict:
    """List the fields extracted from a CRE loan document, with their types and meaning."""
    return {f: {"type": t, "description": DESCRIPTIONS[f]} for f, t in FIELDS.items()}


@server.tool()
def extract_document(path: str, extractor: str = "rules") -> dict:
    """Extract loan fields from a PDF (path relative to the docs root).

    Returns normalized values, the verbatim evidence for each value, and the fields left blank.
    Blank means 'not found with evidence', so route those to a human rather than guessing.
    extractor: "rules" (no model calls) or "hybrid" (rules, then an LLM for missing fields).
    """
    if extractor not in ("rules", "hybrid"):
        raise ToolError("extractor must be 'rules' or 'hybrid'")
    ex = EXTRACTORS[extractor]()
    raw = ex.extract(load_text(_resolve(path)))
    # keep text as written (names, addresses); canonicalize numbers, percents and dates
    values = {f: (str(v).strip() if FIELDS[f] == "text" and v else normalize(FIELDS[f], v)) for f, v in raw.items()}
    return {
        "values": values,
        "evidence": {f: ex.last_evidence.get(f) for f, v in values.items() if v is not None},
        "blank_fields": [f for f, v in values.items() if v is None],
    }


@server.tool()
def evaluate_extractor(extractor: str = "rules") -> dict:
    """Score an extractor on the labelled eval set. Returns overall and per-field accuracy."""
    if extractor not in ("rules", "hybrid"):
        raise ToolError("extractor must be 'rules' or 'hybrid'")
    ex = EXTRACTORS[extractor]()
    rows, latencies = run(ex, DOCS_ROOT)
    summary = score(rows)
    return {"accuracy": summary["accuracy"], "wrong_not_blank": summary["wrong_not_blank"],
            "per_field": summary["per_field"], "per_layout": summary["per_layout"],
            "cost": cost_summary(ex, latencies)}


if __name__ == "__main__":
    server.run()
