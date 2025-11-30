import logging
import os
import uuid
import io
import re
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Dict
import httpx
from fastapi.middleware.cors import CORSMiddleware

from shared.models import TaskEnvelope, CompletionReport
from agents.citation_manager.csl_engine import format_with_csl, format_bibliography_with_csl, _style_path, CITEPROC_AVAILABLE
from agents.citation_manager.engine import (
    normalize_metadata, extract_from_raw_text, merge_metadata, validate,
    process_batch_items, detect_duplicates, save_to_ltm
)
from agents.citation_manager.validators import verify_doi_live, verify_url, fetch_metadata_from_doi, search_metadata_bibliographic

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

# App lifespan hook for startup/shutdown (currently no init)
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint: status and current UTC timestamp
@app.get('/health')
async def health():
    return {"status": "healthy", "agent": "citation_manager", "timestamp": datetime.utcnow().isoformat()}

# Single citation: parse metadata and render via CSL
@app.post('/process', response_model=CompletionReport)
async def process_task(req: Request):
    """
    Parse and format a single citation.

    Reads parameters from a Supervisor-style TaskEnvelope. Accepts either
    free-form `raw_text` and/or partial `metadata`, then normalizes, validates,
    and renders via CSL. Optional LLM-assisted parsing when `llm_parse` is true.

    Persistence:
    - When `save` is true and `user_id` is provided, the normalized item is
      saved into LTM.
    - When `save_all` is true, duplicate checks are bypassed via `force_save`.
    """
    try:
        body = await req.json()
        task_envelope = TaskEnvelope(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request body: {e}")

    params = task_envelope.task.parameters or {}
    agent_data = params.get("agent_specific_data") or {}
    payload = agent_data.get("payload") or {}
    style = agent_data.get("style") or payload.get("style") or params.get("style") or "APA"
    source_type = agent_data.get("source_type") or payload.get("source_type") or params.get("source_type") or "article"
    raw_text = agent_data.get("raw_text") or payload.get("raw_text") or params.get("raw_text") or params.get("request")
    metadata = agent_data.get("metadata") or payload.get("metadata") or params.get("metadata") or {}
    def _pick_bool(*vals, default=False):
        for v in vals:
            if v is not None:
                try:
                    return bool(v)
                except Exception:
                    return default
        return default
    include_doi = _pick_bool(
        params.get("includeDOI"),
        agent_data.get("includeDOI"),
        payload.get("includeDOI"),
        default=True,
    )
    save = _pick_bool(
        params.get("save"),
        agent_data.get("save"),
        payload.get("save"),
        default=False,
    )

    save_all = _pick_bool(
        params.get("save_all"),
        agent_data.get("save_all"),
        payload.get("save_all"),
        default=False,
    )

    user_id = params.get("user_id") or agent_data.get("user_id") or payload.get("user_id")
    llm_parse_flag = (
        agent_data.get("llm_parse")
        or payload.get("llm_parse")
        or params.get("llm_parse")
        or False
    )

    # Fetch metadata from DOI if present and title missing
    if metadata.get("doi") and not metadata.get("title"):
        fetched = fetch_metadata_from_doi(metadata.get("doi"))
        if fetched:
            metadata = merge_metadata(metadata, fetched)

    base_item = normalize_metadata(metadata)
    extracted = extract_from_raw_text(raw_text)
    llm_parsed: Dict = {}
    if llm_parse_flag and raw_text:
        try:
            # Building strict instruction to return JSON only
            prompt = (
                "You are a citation parser. Extract structured metadata as compact JSON only. "
                "Fields: source_type (article|book|web), title, authors (array of strings), year, journal, "
                "publisher, volume, issue, pages, doi, url, isbn, accessed (YYYY-MM-DD or empty). "
                "Return ONLY JSON with these keys."
                f"\n\nText:\n{raw_text}"
            )
            envelope = {
                "message_id": str(uuid.uuid4()),
                "sender": "CitationManagerAgent",
                "recipient": "GeminiWrapperAgent",
                "task": {
                    "name": "llm_parse_citation",
                    "parameters": {"request": prompt}
                }
            }
            # Resolve Gemini Wrapper URL from settings.yaml defaults
            gw_host = os.getenv("GEMINI_WRAPPER_HOST", "127.0.0.1")
            gw_port = int(os.getenv("GEMINI_WRAPPER_PORT", "5010"))
            gw_url = f"http://{gw_host}:{gw_port}/process"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(gw_url, json=envelope)
                if resp.status_code == 200:
                    report = resp.json()
                    out_str = (report.get("results") or {}).get("output") or ""
                    try:
                        llm_parsed = (out_str and isinstance(out_str, str)) and __import__("json").loads(out_str) or {}
                    except Exception:
                        llm_parsed = {}
                else:
                    _logger.warning(f"LLM parse call failed: {resp.status_code} {await resp.aread()}")
        except Exception as e:
            _logger.warning(f"LLM parsing error: {e}")
    # Build merged item before any LLM involvement for UI revert capability
    pre_llm_item = merge_metadata(base_item, extracted)
    merged_item = dict(pre_llm_item)
    if raw_text:
        try:
            merged_item["raw_text"] = raw_text
        except Exception:
            pass
    llm_changes: List[Dict] = []
    if llm_parsed:
        before = dict(merged_item)
        merged_item = merge_metadata(merged_item, llm_parsed)
        try:
            for k, v in (llm_parsed or {}).items():
                prev = before.get(k)
                after = merged_item.get(k)
                if str(prev) != str(after):
                    llm_changes.append({
                        "field": k,
                        "before": prev,
                        "after": after,
                        "source": "LLM"
                    })
        except Exception:
            pass
    live_checks = {}
    if merged_item.get("doi"):
        live_checks["doi_valid"] = verify_doi_live(merged_item["doi"])
    if merged_item.get("url"):
        live_checks["url_valid"] = verify_url(merged_item["url"])
    errors, suggestions, confidence = validate(merged_item, source_type, style)

    # LLM style suggestions when assistant is enabled
    llm_style_suggestions: List[str] = []
    if llm_parse_flag:
        try:
            import json as _json
            md_for_prompt = {
                "source_type": source_type,
                "title": merged_item.get("title") or "",
                "authors": merged_item.get("authors") or [],
                "year": merged_item.get("year") or "",
                "journal": merged_item.get("journal") or "",
                "publisher": merged_item.get("publisher") or "",
                "volume": merged_item.get("volume") or "",
                "issue": merged_item.get("issue") or "",
                "pages": merged_item.get("pages") or "",
                "doi": merged_item.get("doi") or "",
                "url": merged_item.get("url") or ""
            }
            prompt = (
                "You are a citation style auditor. Analyze the metadata strictly for the requested style "
                "and return ONLY a compact JSON array of human-readable suggestions (strings). "
                "Do not include any commentary or keys. Focus on actionable corrections. "
                "Cover case rules, required fields, DOI/URL formatting, page ranges, punctuation, and common style-specific requirements.\n\n"
                f"Style: {style}\n"
                f"SourceType: {source_type}\n"
                f"Metadata: {_json.dumps(md_for_prompt, ensure_ascii=False)}\n\n"
                "Return: [\"Suggestion 1\", \"Suggestion 2\", ...]"
            )
            envelope = {
                "message_id": str(uuid.uuid4()),
                "sender": "CitationManagerAgent",
                "recipient": "GeminiWrapperAgent",
                "task": {
                    "name": "style_suggestions",
                    "parameters": {"request": prompt}
                }
            }
            gw_host = os.getenv("GEMINI_WRAPPER_HOST", "127.0.0.1")
            gw_port = int(os.getenv("GEMINI_WRAPPER_PORT", "5010"))
            gw_url = f"http://{gw_host}:{gw_port}/process"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(gw_url, json=envelope)
                if resp.status_code == 200:
                    report = resp.json()
                    out_str = (report.get("results") or {}).get("output") or ""
                    try:
                        parsed = (out_str and isinstance(out_str, str)) and _json.loads(out_str) or []
                        if isinstance(parsed, list):
                            llm_style_suggestions = [s for s in {str(x).strip() for x in parsed} if s]
                    except Exception:
                        _logger.warning("LLM style suggestions: non-JSON output; ignored")
                else:
                    _logger.warning(f"LLM style suggestions call failed: {resp.status_code}")
        except Exception as e:
            _logger.warning(f"LLM style suggestions error: {e}")

    if llm_style_suggestions:
        suggestions = list({*(suggestions or []), *llm_style_suggestions})

    try:
        # CSL-only rendering for highest compliance; raise helpful error if missing
        formatted = format_with_csl(style, merged_item, source_type=source_type, include_doi=include_doi)
        if save:
            save_to_ltm(merged_item, style, user_id=user_id, force_save=save_all)

        style_path = _style_path(style)
        result_json = {
            "status": "ok" if not errors else "warning",
            "result": {
                "formatted_citation": formatted,
                "style_used": style,
                "confidence": confidence,
                "errors_detected": errors,
                "suggestions": suggestions,
                "suggestions_llm": llm_style_suggestions,
                "live_checks": live_checks,
                "parsed_metadata": merged_item,
                "pre_llm_metadata": pre_llm_item,
                "llm_applied_changes": llm_changes,
                "source_type_used": source_type
            },
            "meta": {
                "agent": "citation_manager",
                "version": "1.1.0",
                "timestamp": datetime.utcnow().isoformat(),
                "render_engine": "CSL",
                "csl_style_path": style_path
            }
        }

        import json
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender="CitationManagerAgent",
            recipient=task_envelope.sender,
            related_message_id=task_envelope.message_id,
            status="SUCCESS",
            results={"output": json.dumps(result_json), "cached": False}
        )
    except Exception as e:
        _logger.error(f"Formatting error: {e}")
        raise HTTPException(status_code=500, detail=f"Formatting failed: {str(e)}")

# Batch citations: normalize items and return bibliography
@app.post("/batch", response_model=CompletionReport)
async def batch_process(req: Request):
    try:
        body = await req.json()
        task_envelope = TaskEnvelope(**body)
        params = task_envelope.task.parameters or {}
        items = params.get("items") or []
        style = (params.get("style") or "APA").upper()
        include_doi = params.get("includeDOI", True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")

    processed = process_batch_items(items)
    formatted = format_bibliography_with_csl(style, processed, include_doi=include_doi)

    result = {
        "status": "ok",
        "result": {
            "formatted_bibliography": formatted,
            "count": len(processed)
        },
        "meta": {"agent": "citation_manager", "version": "1.1.0", "timestamp": datetime.utcnow().isoformat()}
    }
    import json
    return CompletionReport(
        message_id=str(uuid.uuid4()),
        sender="CitationManagerAgent",
        recipient=task_envelope.sender,
        related_message_id=task_envelope.message_id,
        status="SUCCESS",
        results={"output": json.dumps(result), "cached": False}
    )

# LTM retrieval endpoint
@app.post("/ltm/retrieve", response_model=CompletionReport)
async def ltm_retrieve(req: Request):
    try:
        body = await req.json()
        task_envelope = TaskEnvelope(**body)
        params = task_envelope.task.parameters or {}
        agent_data = params.get("agent_specific_data") or {}
        payload = agent_data.get("payload") or {}

        user_id = params.get("user_id") or agent_data.get("user_id") or payload.get("user_id")
        query = params.get("query") or payload.get("query")
        style = params.get("style") or payload.get("style")
        limit = int(params.get("limit") or payload.get("limit") or 50)
        since = params.get("since") or payload.get("since")
        until = params.get("until") or payload.get("until")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")

    try:
        from .ltm import search_citations
        rows = search_citations(user_id=user_id, query=query, style=style, limit=limit, since=since, until=until)
        result = {
            "status": "ok",
            "result": {"items": rows, "count": len(rows)},
            "meta": {"agent": "citation_manager", "version": "1.1.0", "timestamp": datetime.utcnow().isoformat()}
        }
        import json
        return CompletionReport(
            message_id=str(uuid.uuid4()),
            sender="CitationManagerAgent",
            recipient=task_envelope.sender,
            related_message_id=task_envelope.message_id,
            status="SUCCESS",
            results={"output": json.dumps(result), "cached": False}
        )
    except Exception as e:
        _logger.error(f"LTM retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"LTM retrieval failed: {str(e)}")

# Convert a single item to another citation style (CSL)
@app.post("/convert", response_model=CompletionReport)
async def convert(req: Request):
    try:
        body = await req.json()
        task_envelope = TaskEnvelope(**body)
        params = task_envelope.task.parameters or {}
        item = params.get("metadata") or {}
        from_style = (params.get("from_style") or "APA").upper()
        to_style = (params.get("to_style") or "MLA").upper()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")

    # Convert is just re-render in the target style via CSL
    converted = format_with_csl(to_style, item, include_doi=True)
    result = {"status": "ok", "result": {"converted": converted}}
    import json
    return CompletionReport(
        message_id=str(uuid.uuid4()),
        sender="CitationManagerAgent",
        recipient=task_envelope.sender,
        related_message_id=task_envelope.message_id,
        status="SUCCESS",
        results={"output": json.dumps(result), "cached": False}
    )

# Bibliography generator 
@app.post("/bibliography", response_model=CompletionReport)
async def bibliography(req: Request):
    """
    Format a bibliography for a batch of items.

    Parameters via TaskEnvelope.task.parameters:
    - `items`: list of metadata dicts
    - `style`: target style (APA/MLA/etc.)
    - `remove_duplicates`: if true, runs a simple duplicate detection pass
    - `save`, `user_id`, `save_all`: when saving is requested, persist items
      to LTM; if `save_all` is true, bypass duplicate checks.
    Returns CompletionReport with `formatted_bibliography` and `count`.
    """
    try:
        body = await req.json()
        task_envelope = TaskEnvelope(**body)
        params = task_envelope.task.parameters or {}
        items = params.get("items") or []
        style = (params.get("style") or "APA").upper()
        remove_dups = params.get("remove_duplicates", True)
        # Saving controls
        save = bool(params.get("save") or False)
        user_id = params.get("user_id") or None
        save_all = bool(params.get("save_all") or False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")

    processed = process_batch_items(items)
    if remove_dups:
        processed = detect_duplicates(processed)
    formatted = format_bibliography_with_csl(style, processed)
    try:
        if save:
            items_to_save = process_batch_items(items) if save_all else processed
            for it in items_to_save:
                try:
                    save_to_ltm(it, style, user_id=user_id, force_save=save_all)
                except Exception:
                    pass
    except Exception:
        pass
    result = {
        "status": "ok",
        "result": {"formatted_bibliography": formatted, "count": len(processed)}
    }
    import json
    return CompletionReport(
        message_id=str(uuid.uuid4()),
        sender="CitationManagerAgent",
        recipient=task_envelope.sender,
        related_message_id=task_envelope.message_id,
        status="SUCCESS",
        results={"output": json.dumps(result), "cached": False}
    )


# CSL diagnostic: check style paths and citeproc availability
@app.get("/csl_status")
async def csl_status():
    styles = ["APA", "MLA", "Chicago", "Harvard", "IEEE"]
    status_map: Dict[str, Dict[str, object]] = {}
    for s in styles:
        p = _style_path(s)
        status_map[s] = {"path": p, "exists": os.path.exists(p)}
    return {
        "citeproc_available": CITEPROC_AVAILABLE,
        "style_dir_env": os.environ.get("CSL_STYLE_DIR"),
        "styles": status_map,
    }

# Extract references section text from a PDF blob
def _extract_references_text_from_pdf_bytes(data: bytes) -> str:
    """Extract the references/bibliography section text from a PDF.
    Preferred: PyMuPDF (fitz) for robust extraction; fallback to pdfplumber.
    Heuristics: look for headings 'References', 'Bibliography', 'Works Cited'.
    Fallback: return full text if no heading found.
    """
    text_chunks: List[str] = []
    try:
        import fitz  
        doc = fitz.open(stream=data, filetype="pdf")
        try:
            for page in doc:
                try:
                    txt = page.get_text("text") or ""
                except Exception:
                    txt = ""
                if txt:
                    text_chunks.append(txt)
        finally:
            doc.close()
    except Exception:
        try:
            import pdfplumber  
        except Exception as e:
            raise HTTPException(status_code=501, detail=f"PDF parsing libraries missing: {e}. Install PyMuPDF (pymupdf) or pdfplumber.")
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                try:
                    txt = page.extract_text() or ""
                except Exception:
                    txt = ""
                if txt:
                    text_chunks.append(txt)
    full_text = "\n".join(text_chunks)
    pattern = re.compile(r"^(References|Bibliography|Works Cited)\b", re.I | re.M)
    m = pattern.search(full_text)
    if not m:
        return full_text
    start_idx = m.start()
    return full_text[start_idx:]

# Split references text into individual candidate entries
def _split_candidate_references(ref_text: str) -> List[str]:
    """Split references text into candidate entries using simple heuristics."""
    lines = [ln.strip() for ln in (ref_text or "").splitlines()]
    entries: List[str] = []
    buf: List[str] = []
    def flush():
        if buf:
            entry = " ".join(buf)
            entry = re.sub(r"\s+", " ", entry).strip()
            if len(entry) > 40:  
                entries.append(entry)
            buf.clear()
    for ln in lines:
        if not ln:
            flush()
            continue
        if re.match(r"^(\d+\.|\[\d+\]|•|-)\s+", ln):
            flush()
            buf.append(ln)
        else:
            buf.append(ln)
    flush()
    if len(entries) < 3:
        paras = [p.strip() for p in re.split(r"\n\s*\n", ref_text or "") if p.strip()]
        if len(paras) > len(entries):
            entries = [re.sub(r"\s+", " ", p).strip() for p in paras if len(p) > 40]
    return entries

# Parse a single reference with LLM to enrich metadata
async def _llm_parse_reference(ref: str) -> Dict:
    """Use LLM to parse a single reference string into structured metadata."""
    gw_host = os.getenv("GEMINI_WRAPPER_HOST", "127.0.0.1")
    gw_port = int(os.getenv("GEMINI_WRAPPER_PORT", "5010"))
    gw_url = f"http://{gw_host}:{gw_port}/process"
    prompt = (
        "You are a citation parser. Extract structured metadata as compact JSON only. "
        "Fields: source_type (article|book|web), title, authors (array of strings), year, journal, "
        "publisher, volume, issue, pages, doi, url. Return ONLY JSON with these keys.\n\n"
        f"Reference: {ref}"
    )
    envelope = {
        "message_id": str(uuid.uuid4()),
        "sender": "CitationManagerAgent",
        "recipient": "GeminiWrapperAgent",
        "task": {"name": "llm_parse_citation", "parameters": {"request": prompt}},
    }
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(gw_url, json=envelope)
            if resp.status_code == 200:
                report = resp.json()
                out_str = (report.get("results") or {}).get("output") or ""
                import json as _json
                try:
                    parsed = (out_str and isinstance(out_str, str)) and _json.loads(out_str) or {}
                    return parsed if isinstance(parsed, dict) else {}
                except Exception:
                    return {}
            else:
                _logger.warning(f"LLM parse failed: {resp.status_code}")
                return {}
    except Exception as e:
        _logger.warning(f"LLM parse error: {e}")
        return {}

# Upload and process PDF: extract references and produce bibliography
@app.post('/upload/pdf', response_model=CompletionReport)
async def upload_pdf(
    file: UploadFile = File(...),
    style: str = "APA",
    includeDOI: bool = True,
    llm_parse: bool = True,
    save: bool = False,
    user_id: str | None = None,
    save_all: bool = False,
):
    """
    Extract references from an uploaded PDF and return normalized/validated
    items and a formatted bibliography.

    - Honors `style`, `includeDOI`, and `llm_parse` for formatting/parsing.
    - When `save` is true and `user_id` provided, saves items to LTM.
    - When `save_all` is true, bypasses duplicate checks during save.
    """
    try:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Empty PDF upload")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {e}")

    # Extract references text and split into candidate entries
    ref_text = _extract_references_text_from_pdf_bytes(data)
    candidates = _split_candidate_references(ref_text)
    from agents.citation_manager.engine import normalize_metadata, extract_from_raw_text

    parsed_items: List[Dict] = []
    items_formatted: List[str] = []
    items_validation: List[Dict] = []
    start_time = datetime.utcnow()
    time_budget_s = int(os.getenv("PDF_PROCESS_TIME_BUDGET", "150"))
    processed_count = 0
    total_candidates = len(candidates)

    def _postprocess_item(item: Dict) -> Dict:
        """Light cleanup and enrichment heuristics to reduce raw/messy entries."""
        i = dict(item or {})
        for k in ["title", "journal", "publisher", "url"]:
            v = i.get(k)
            if isinstance(v, str):
                i[k] = re.sub(r"\s+", " ", v).strip().strip(" .,")
        authors = i.get("authors") or []
        if isinstance(authors, list):
            i["authors"] = [re.sub(r"\s+", " ", (a or "")).strip() for a in authors if a]
            STOP = {"journal", "proc.", "proceedings", "algebra", "math", "math.", "appl.", "applied", "pure", "transactions", "ann.", "soc.", "society", "forum"}
            def _looks_journalish(name: str) -> bool:
                low = name.lower()
                if re.search(r"\bJ\.?\s*[A-Z]", name):
                    return True
                toks = re.split(r"\s+", low)
                return any(t.strip(".,()[]") in STOP for t in toks)
            if i.get("journal"):
                i["authors"] = [a for a in i["authors"] if not _looks_journalish(a)]
        if not i.get("year") and isinstance(i.get("raw_text"), str):
            m = re.search(r"\b(19\d{2}|20\d{2}|21\d{2})\b", i["raw_text"])
            if m:
                try:
                    i["year"] = int(m.group(0))
                except Exception:
                    pass
        raw = i.get("raw_text") or ""
        m_arx = re.search(r"arXiv\s*:\s*([0-9.]+)(?:v\d+)?", raw, re.I)
        if m_arx:
            i.setdefault("journal", "arXiv")
            i.setdefault("source_type", "article")
            i.setdefault("url", f"https://arxiv.org/abs/{m_arx.group(1)}")
        return i
    for ref in candidates:
        if (datetime.utcnow() - start_time).total_seconds() > time_budget_s:
            break
        md: Dict = {}
        md = extract_from_raw_text(ref)
        if llm_parse:
            sparse = not (md.get("title") and md.get("authors") and md.get("year"))
            if sparse:
                try:
                    llm_md = await _llm_parse_reference(ref)
                    if llm_md:
                        from agents.citation_manager.engine import merge_metadata
                        md = merge_metadata(md, llm_md)
                except Exception:
                    pass
        if ref:
            md = {**md, "raw_text": ref}
        item = normalize_metadata(md)
        try:
            sparse = not (item.get("title") and item.get("authors") and item.get("year"))
            if includeDOI and (sparse or not item.get("doi")):
                enriched = search_metadata_bibliographic(ref)
                if enriched:
                    from agents.citation_manager.engine import merge_metadata
                    item = merge_metadata(item, enriched)
        except Exception:
            pass
        try:
            if item.get("doi") and not item.get("title"):
                fetched = fetch_metadata_from_doi(item["doi"])
                if fetched:
                    from agents.citation_manager.engine import merge_metadata
                    item = merge_metadata(item, fetched)
        except Exception:
            pass
        item = _postprocess_item(item)

        live_checks = {}
        try:
            if item.get("doi"):
                live_checks["doi_valid"] = verify_doi_live(item["doi"])
            if item.get("url"):
                live_checks["url_valid"] = verify_url(item["url"])
        except Exception:
            pass
        try:
            errs, suggs, conf = validate(item, (item.get("source_type") or "article"), style)
        except Exception:
            errs, suggs, conf = [], [], 0.0
        items_validation.append({"errors": errs, "suggestions": suggs, "confidence": conf, "live_checks": live_checks})
        try:
            formatted_item = format_with_csl(style, item, source_type=(item.get("source_type") or "article"), include_doi=includeDOI)
        except Exception:
            formatted_item = ""
        items_formatted.append(formatted_item)
        parsed_items.append(item)
        try:
            if save:
                save_to_ltm(item, style, user_id=user_id, force_save=save_all)
        except Exception as e:
            _logger.warning(f"Failed to save citation to LTM (streaming): {e}")
        processed_count += 1

    try:
        formatted = format_bibliography_with_csl(style, parsed_items, include_doi=includeDOI)
    except Exception as e:
        _logger.error(f"Bibliography formatting error: {e}")
        formatted = ""

    result = {
        "status": "ok",
        "result": {
            "formatted_bibliography": formatted,
            "items": parsed_items,
            "items_formatted": items_formatted,
            "items_validation": items_validation,
            "count": len(parsed_items),
            "style_used": style,
            "include_doi": includeDOI,
            "llm_parse": llm_parse,
            "raw_references_text": ref_text,
            "truncated": processed_count < total_candidates,
            "processed_count": processed_count,
            "total_candidates": total_candidates,
            "time_budget_seconds": time_budget_s,
        },
        "meta": {"agent": "citation_manager", "version": "1.2.1", "timestamp": datetime.utcnow().isoformat()},
    }
    import json
    return CompletionReport(
        message_id=str(uuid.uuid4()),
        sender="CitationManagerAgent",
        recipient="UI",
        related_message_id=str(uuid.uuid4()),
        status="SUCCESS",
        results={"output": json.dumps(result), "cached": False},
    )
