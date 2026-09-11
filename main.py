import datetime
import os
import sqlite3

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from audit import (
    audit_tender,
    corpus_evidence,
    list_decisions,
    neighbourhood,
    record_decision,
)
from engine import (
    check_certification,
    check_dead_citation,
    corpus_stats,
    extract_citations,
    extract_document,
    full_graph,
    list_backlog,
    list_certifications,
    list_standards,
    list_tenders,
    match_spec,
    related_standards,
    run_benchmark,
    standard_detail,
)

DB_PATH = "manak_setu.db"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
# A pasted body larger than this is not a tender clause, it is an accident or a
# probe. Bounded here so the limit is a stated rule rather than whatever the
# process happens to survive.
MAX_TEXT_CHARS = 400_000
VERSION = "0.4"

def _dataset_date() -> str:
    """Newest mtime across the source CSVs — what an operator checks to see
    how stale the register is."""
    newest = 0.0
    for name in os.listdir("data") if os.path.isdir("data") else []:
        if name.endswith(".csv"):
            newest = max(newest, os.path.getmtime(os.path.join("data", name)))
    if not newest:
        return "unknown"
    return datetime.date.fromtimestamp(newest).strftime("%d %b %Y")

app = FastAPI(title="MANAK-SETU Backend")

@app.middleware("http")
async def no_store(request, call_next):
    """Data changes when the CSVs are rebuilt; a browser holding yesterday's
    /graph or /stats shows stale counts with no visible error."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, must-revalidate"
    return response


# The graph and standards payloads are highly repetitive JSON; over a tunnel or
# a phone connection the transfer, not the query, is what makes the page wait.
app.add_middleware(GZipMiddleware, minimum_size=1024)

# Same-origin in every deployment we run: FastAPI serves the frontend itself, so
# the browser never makes a cross-origin call. The list stays configurable for a
# split deploy, but it defaults to closed rather than open — /decision writes to
# the audit log, and "*" would let anyone who finds the URL write to it.
_origins = [o.strip() for o in os.getenv("MANAK_ALLOWED_ORIGINS", "").split(",") if o.strip()]
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )


class AnalyzeRequest(BaseModel):
    spec_text: str | None = None
    cited_is_numbers: list[str] = []


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    response = {
        "matched_standards": None,
        "dead_citations": {},
        "certifications": {},
        "related": {},
    }

    if req.spec_text:
        response["matched_standards"] = match_spec(req.spec_text)

    for is_number in req.cited_is_numbers:
        response["dead_citations"][is_number] = check_dead_citation(is_number)
        response["certifications"][is_number] = check_certification(is_number)
        response["related"][is_number] = related_standards(is_number)

    return response


async def _read_upload(file: UploadFile) -> bytes:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 25 MB limit")
    return content


def _extract_or_422(content: bytes, filename: str | None) -> dict:
    try:
        return extract_document(content, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse document: {exc}") from exc


class TextRequest(BaseModel):
    text: str


class AuditTextRequest(BaseModel):
    text: str = ""
    cited: list[str] | None = None
    document: str | None = None


@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    """Text and literal IS-number citations from an uploaded PDF or .docx."""
    return _extract_or_422(await _read_upload(file), file.filename)


@app.post("/audit-tender")
async def audit_tender_upload(file: UploadFile = File(...)):
    """Audit screen, file path: extract, then report dispute risk, statutory
    omissions and standards comparable tenders cite but this one omits."""
    extracted = _extract_or_422(await _read_upload(file), file.filename)
    result = audit_tender(
        extracted.get("text", ""),
        filename=file.filename,
        cited=extracted.get("citations", []),
    )
    result["extraction"] = {
        k: extracted.get(k)
        for k in ("format", "page_count", "pages_read", "characters", "chars_per_page",
                  "tables", "scanned", "scanned_note")
    }
    if extracted.get("scanned"):
        # A scan yields no text layer, so "no findings" would be a lie of omission.
        result["verdict"] = "unreadable"
        result["summary"] = extracted["scanned_note"]
    return result


@app.post("/audit-text")
def audit_tender_text(req: AuditTextRequest):
    """Same audit for pasted text, or for citations queued by hand. The demo
    path, and the fallback when a PDF turns out to be a scan."""
    if len(req.text or "") > MAX_TEXT_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Text exceeds {MAX_TEXT_CHARS:,} characters. Upload the document instead.",
        )
    cited = [c.strip() for c in (req.cited or []) if c and c.strip()] or None
    if not (req.text or "").strip() and not cited:
        raise HTTPException(
            status_code=400, detail="Provide specification text or at least one IS number"
        )
    return audit_tender(req.text or "", filename=req.document or "pasted text", cited=cited)


class RecommendRequest(BaseModel):
    spec_text: str
    ui_language: str | None = None


class DecisionRequest(BaseModel):
    officer: str
    decision: str
    finding_kind: str | None = None
    is_number: str | None = None
    document: str | None = None
    rationale: str | None = None
    system_said: str | None = None


@app.post("/extract-text")
def extract_text(req: TextRequest):
    return {"citations": extract_citations(req.text), "characters": len(req.text)}


@app.post("/recommend")
def recommend(req: RecommendRequest):
    """Forward flow: spec text -> governing standard, related, certification,
    composed clause. Hybrid retrieval decides; composition only phrases."""
    from retrieval import recommend as _recommend

    if not req.spec_text.strip():
        raise HTTPException(status_code=400, detail="spec_text is empty")
    if len(req.spec_text) > MAX_TEXT_CHARS:
        raise HTTPException(
            status_code=413, detail=f"spec_text exceeds {MAX_TEXT_CHARS:,} characters"
        )
    return _recommend(req.spec_text.strip(), req.ui_language)


@app.get("/graph")
def graph(nodes: int | None = None, edges: int | None = None):
    """Full co-citation graph, or a top-degree sample when `nodes`/`edges` are
    given — the overview's decorative figure does not need 600 KB."""
    return full_graph(node_limit=nodes, edge_limit=edges)


@app.get("/standards")
def standards():
    return list_standards()


@app.get("/standard")
def standard(is_number: str):
    return standard_detail(is_number)


@app.get("/certifications")
def certifications():
    return list_certifications()


@app.get("/tenders")
def tenders():
    return list_tenders()


@app.get("/backlog")
def backlog():
    return list_backlog()


@app.get("/stats")
def stats():
    return corpus_stats()


@app.get("/benchmark")
def benchmark():
    return run_benchmark()


@app.get("/graph/{is_number:path}")
def graph_neighbourhood(is_number: str, depth: int = 1):
    """The graph around one standard — what the evidence panel draws."""
    return neighbourhood(is_number, depth=depth)


@app.get("/evidence")
def evidence(is_number: str):
    """Which real published tenders cite this standard, with their links."""
    return corpus_evidence(is_number)


@app.post("/decision")
def decision(req: DecisionRequest):
    """Log an officer's verdict on a finding. The system recommends; a person
    decides; the decision is what an auditor reads a year later."""
    try:
        return record_decision(
            officer=req.officer,
            decision=req.decision,
            finding_kind=req.finding_kind,
            is_number=req.is_number,
            document=req.document,
            rationale=req.rationale,
            system_said=req.system_said,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/decisions")
def decisions(limit: int = 200):
    return list_decisions(limit=limit)


class QueryRequest(BaseModel):
    text: str
    route: str | None = None      # "draft" | "audit" to override the router


@app.post("/query")
def query(req: QueryRequest):
    """Orchestration: one entry point, routed by what the text actually is.

    A specification names a product and wants a standard. A tender already cites
    standards and wants them checked. Callers that cannot know which they hold —
    the browser extension, a future integration — post here and let the router
    decide, with its reasoning returned so the choice is never invisible."""
    from engine import extract_citations

    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is empty")
    if len(text) > MAX_TEXT_CHARS:
        raise HTTPException(status_code=413, detail=f"text exceeds {MAX_TEXT_CHARS:,} characters")

    citations = extract_citations(text)
    # The router reads citations, which survive translation, so it can decide
    # before any language handling happens.
    if req.route in ("draft", "audit"):
        route, why = req.route, "caller specified the route"
    elif len(citations) >= 2:
        route = "audit"
        why = (f"{len(citations)} IS numbers are already cited, so this reads as an existing "
               "tender to be checked rather than a specification needing one")
    elif citations:
        route = "audit"
        why = ("one standard is already cited, so it is checked rather than replaced")
    else:
        route = "draft"
        why = "no IS number is cited, so this reads as a specification needing a standard"

    routing = {"route": route, "reason": why, "citations_found": len(citations)}
    if route == "audit":
        result = audit_tender(text, filename="routed query", cited=citations or None)
    else:
        from retrieval import recommend as _recommend

        result = _recommend(text)
    return {"routing": routing, "result": result}


class TranslateRequest(BaseModel):
    texts: list[str]
    target: str


@app.post("/translate")
def translate(req: TranslateRequest):
    """Translate interface text for the language switcher.

    Cached on disk and keyed by (target, text), because a government console
    shows the same few hundred labels to everyone: the first viewer in a
    language pays for the call, nobody after them does. Without the cache a
    free-tier quota is gone in a handful of page loads.

    This endpoint is for *interface* text. Standard titles and IS numbers are
    excluded by the caller and never sent.
    """
    import multilingual

    if not req.texts:
        return {"translations": {}, "cached": 0, "fetched": 0}
    if len(req.texts) > 400:
        raise HTTPException(status_code=413, detail="At most 400 strings per request")
    return multilingual.translate_ui_batch(req.texts, req.target)


@app.get("/llm")
def llm_status():
    """Whether a local model is actually available. The UI reads this so the
    clause panel can say how the text in front of you was produced."""
    import llm

    return llm.status()


@app.get("/health")
def health():
    conn = sqlite3.connect(DB_PATH)
    try:
        counts = {}
        for table in (
            "standards",
            "tenders",
            "co_citation",
            "certification_rules",
            "coverage_gap_backlog",
        ):
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        import llm
        from retrieval import LIGHT_MODE

        return {
            "status": "ok",
            "retrieval_mode": "light (no cross-encoder)" if LIGHT_MODE else "full",
            "version": VERSION,
            "dataset_date": _dataset_date(),
            "row_counts": counts,
            "llm": llm.status(),
        }
    finally:
        conn.close()


class NoCacheStatic(StaticFiles):
    """Browsers were serving a stale app.js after edits, because a cache-buster
    on the page URL does not invalidate its subresources. Demo machines must
    never show yesterday's build."""

    def is_not_modified(self, *args, **kwargs) -> bool:
        return False

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, must-revalidate"
        return response


# Mounted last so it never shadows the API routes above. Serving the UI from the
# same origin means there is one port to share when demoing over LAN or a tunnel.
if os.path.isdir("frontend"):
    app.mount("/", NoCacheStatic(directory="frontend", html=True), name="frontend")
