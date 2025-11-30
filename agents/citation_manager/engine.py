import re
from typing import Dict, List, Tuple
from .validators import fetch_metadata_from_doi, verify_doi_live, doi_syntax_is_valid

# Split an author string into a clean list of names
def _split_authors(author_str: str) -> List[str]:
    if not author_str:
        return []
    parts = [p.strip() for p in re.split(r"[;,]", author_str) if p.strip()]
    return parts if parts else [author_str.strip()]

# Normalize raw metadata fields (authors, DOI, pages, passthrough)
def normalize_metadata(metadata: Dict) -> Dict:
    md = metadata or {}
    authors_field = md.get("author") or md.get("authors")
    authors = authors_field if isinstance(authors_field, list) else _split_authors(authors_field or "")
    doi = md.get("doi")
    if isinstance(doi, str) and doi:
        d = doi.strip()
        if d.lower().startswith("http://doi.org/") or d.lower().startswith("https://doi.org/") or \
           d.lower().startswith("doi:"):
            # strip known prefixes
            d = d.replace("DOI:", "", 1).replace("doi:", "", 1)
            if "doi.org/" in d.lower():
                d = d.split("doi.org/", 1)[-1]
        doi = d.strip().lower()
    else:
        doi = md.get("doi")
    pages = md.get("pages")
    if isinstance(pages, str) and pages:
        p = pages.strip()
        p = re.sub(r"\s*[-–—‑]\s*", "-", p)
        pages = p
    else:
        pages = md.get("pages")
    return {
        "title": md.get("title", ""),
        "authors": authors,
        "year": md.get("year"),
        "journal": md.get("journal"),
        "publisher": md.get("publisher"),
        "volume": md.get("volume"),
        "issue": md.get("issue"),
        "pages": pages,
        "doi": doi,
        "url": md.get("url"),
        "raw_text": md.get("raw_text"),
        "source_type": md.get("source_type"),
    }

# Extract minimal metadata heuristics from free-form reference text
def extract_from_raw_text(raw: str) -> Dict:
    if not raw:
        return {}
    extracted = {}
    m_doi = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", raw, re.I)
    m_url = re.search(r"https?://\S+", raw)
    m_year = re.search(r"\((\d{4})\)|\b(\d{4})\b", raw)
    m_title = re.search(r"\"([^\"]{3,})\"|“([^”]{3,})”|‘([^’]{3,})’|'([^']{3,})'", raw)

    extracted["doi"] = m_doi.group(0) if m_doi else None
    extracted["url"] = m_url.group(0) if m_url else None
    if m_year:
        extracted["year"] = m_year.group(1) or m_year.group(2)
    if m_title:
        for i in range(1, 5):
            if m_title.group(i):
                extracted["title"] = m_title.group(i)
                break
    else:
        segs = [s.strip() for s in re.split(r",", raw) if s.strip()]
        STOP = {"journal", "proc.", "proceedings", "algebra", "math", "math.", "appl.", "applied", "pure", "transactions", "ann.", "soc.", "society", "forum"}
        def is_journalish(s: str) -> bool:
            low = s.lower()
            if re.search(r"\bJ\.?\s*[A-Z]", s):
                return True
            if re.search(r"\b\d+\s*\(\d{4}\)\b", s):
                return True
            toks = re.split(r"\s+", low)
            return any(t.strip(".,()[]") in STOP for t in toks)
        def is_titleish(s: str) -> bool:
            words = [w for w in re.split(r"\s+", s) if w]
            if len(words) < 3:
                return False
            lowers = sum(1 for w in words if re.match(r"^[a-z]", w))
            return lowers >= max(2, len(words)//3)
        title_candidate = None
        author_segments = []
        for seg in segs:
            if is_journalish(seg):
                break
            if not title_candidate and is_titleish(seg):
                title_candidate = seg
                break
            else:
                author_segments.append(seg)
        if title_candidate:
            extracted["title"] = title_candidate.strip().strip(" .")
        names_raw = ", ".join(author_segments)
        candidates = [n.strip() for n in re.split(r";|,| and ", names_raw) if n.strip()]
        filtered: List[str] = []
        for c in candidates:
            low = c.lower()
            if is_journalish(c):
                continue
            if len(low.split()) < 2:
                continue
            filtered.append(c)
        if filtered:
            extracted["authors"] = list(dict.fromkeys(filtered))
    return extracted

# Merge extracted hints into base without overwriting filled fields
def merge_metadata(base: Dict, extracted: Dict) -> Dict:
    merged = dict(base)
    for k, v in extracted.items():
        if not merged.get(k) and v:
            merged[k] = v
    return merged

# Validate item for source type and style; return errors/suggestions/confidence
def validate(item: Dict, source_type: str, style: str = None) -> Tuple[List[str], List[str], float]:
    errors: List[str] = []
    suggestions: List[str] = []
    required_common = ["title", "year"]
    for f in required_common:
        if not item.get(f):
            errors.append(f"Missing required field: {f}")
    st = (source_type or "article").lower()
    if st in ["article", "journal"]:
        if not item.get("journal"):
            suggestions.append("Add 'journal' for journal articles.")
        if not item.get("authors"):
            suggestions.append("Provide at least one author.")
    elif st in ["book"]:
        if not item.get("publisher"):
            suggestions.append("Add 'publisher' for books.")
    elif st in ["web", "website"]:
        if not item.get("url"):
            suggestions.append("Provide a URL for web sources.")

    # DOI checks
    if not item.get("doi"):
        suggestions.append("Consider adding DOI if available.")
    else:
        doi_val = str(item.get("doi") or "").strip()
        if not doi_syntax_is_valid(doi_val):
            errors.append("Invalid DOI syntax.")

    # URL scheme sanity check
    if item.get("url"):
        url = str(item.get("url") or "").strip()
        if not re.match(r"^https?://", url, re.IGNORECASE):
            errors.append("URL must start with http:// or https://")

    # Capitalization heuristic for title
    title = (item.get("title") or "").strip()
    if title:
        if title.isupper():
            suggestions.append("Title appears to be ALL CAPS; adjust capitalization.")
        elif title.islower():
            suggestions.append("Title appears to be all lowercase; adjust capitalization.")

    # Deep data quality checks (lightweight heuristics)
    if item.get("year"):
        try:
            y = int(item["year"]) 
            if y < 1500 or y > 2100:
                errors.append("Year looks out of plausible range (1500–2100).")
        except Exception:
            errors.append("Year must be numeric.")
    if item.get("volume") and not re.match(r"^\d+$", str(item.get("volume"))):
        suggestions.append("Volume should be numeric.")
    if item.get("issue") and not re.match(r"^\d+$", str(item.get("issue"))):
        suggestions.append("Issue should be numeric.")
    if item.get("pages"):
        pages_str = str(item.get("pages")).strip()
        if not re.match(r"^(?:\d+|[A-Za-z]?\d+\s*[-–—‑]\s*[A-Za-z]?\d+)$", pages_str):
            suggestions.append("Pages should look like '12-34'.")

    # Duplicate check disabled for online mode: no local-store blocking errors
    keys_for_conf = ["title", "authors", "year", "journal", "publisher", "volume", "issue", "pages", "doi", "url"]
    filled = sum(1 for k in keys_for_conf if item.get(k))
    confidence = round(filled / len(keys_for_conf), 2)

    # Style-aware suggestions (lightweight heuristics)
    if style:
        s = (style or "").strip().lower()
        if s == "apa":
            if title:
                words = [w for w in re.split(r"\s+", title) if w]
                caps = sum(1 for w in words if re.match(r"^[A-Z]", w))
                if len(words) >= 4 and caps > len(words) / 2:
                    suggestions.append("APA: Convert title to sentence case (capitalize first word and proper nouns).")
            if not item.get("doi") and st in ["article", "journal"]:
                suggestions.append("APA: Include DOI if available for journal articles.")
        elif s == "mla":
            if st in ["web", "website"]:
                suggestions.append("MLA: Include access date for web sources (optional but common).")
            if st in ["article", "journal"] and not item.get("pages"):
                suggestions.append("MLA: Add page range for articles when applicable.")
        elif s == "chicago":
            if st in ["book"] and not item.get("publisher"):
                suggestions.append("Chicago: Include publisher for books and consider publisher location.")
            if st in ["article", "journal"] and not item.get("pages"):
                suggestions.append("Chicago: Provide page range for articles when available.")
        elif s == "harvard":
            if st in ["article", "journal"] and not item.get("pages"):
                suggestions.append("Harvard: Include page numbers for journal articles when applicable.")
            if st in ["web", "website"] and not item.get("url"):
                suggestions.append("Harvard: Provide the URL for web sources.")
        elif s == "ieee":
            if not item.get("doi") and st in ["article", "journal"]:
                suggestions.append("IEEE: Include DOI if available for journal articles.")
            if item.get("journal"):
                suggestions.append("IEEE: Use standard journal abbreviation if known.")

    return errors, suggestions, confidence

# Batch processing: normalize list of raw items into metadata
def process_batch_items(items: List[Dict]) -> List[Dict]:
    processed = []
    for raw in items:
        if isinstance(raw, str):
            extracted = extract_from_raw_text(raw)
            md = normalize_metadata({})
            merged = merge_metadata(md, extracted)
        else:
            md = normalize_metadata(raw)
            extracted = extract_from_raw_text(raw.get("raw_text") or "")
            merged = merge_metadata(md, extracted)
            if merged.get("doi") and not merged.get("title"):
                fetched = fetch_metadata_from_doi(merged["doi"])
                if fetched:
                    merged = merge_metadata(merged, fetched)
        processed.append(merged)
    return processed

# Duplicate detection (simple: same doi or title)
def detect_duplicates(items: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for it in items:
        key = (it.get("doi") or "").lower() or (it.get("title") or "").strip().lower()
        if not key:
            out.append(it)
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out

# Style conversion (metadata-based)
def convert_style(item: Dict, from_style: str, to_style: str) -> Dict:
    md = normalize_metadata(item)
    return {"metadata": md, "from": from_style, "to": to_style}


from .ltm import save_citation as _save_citation
from .ltm import exists_duplicate as _exists_duplicate
def save_to_ltm(item: Dict, style: str, user_id: str | None = None, force_save: bool = False):
    """Render citation via CSL for LTM storage with sensible fallbacks and duplicate/empty guards.

    When `force_save` is True, duplicate checks are bypassed so all items persist.
    """
    if not ((item.get("title") and str(item.get("title")).strip()) or item.get("doi") or item.get("url") or item.get("raw_text")):
        return

    if not force_save:
        try:
            if _exists_duplicate and (_exists_duplicate(doi=(item.get("doi") or None), title=(item.get("title") or None))):
                return
        except Exception:
            pass

    # Try CSL formatting first
    formatted = ""
    try:
        from .csl_engine import format_with_csl
        formatted = format_with_csl(style or "APA", item, include_doi=True)
    except Exception:
        formatted = ""

    # Fallback formatting if CSL fails or yields empty string
    if not (formatted or "").strip():
        raw = str(item.get("raw_text") or "").strip()
        if raw:
            formatted = raw
        else:
            title = str(item.get("title") or "Untitled").strip()
            year = str(item.get("year") or "n.d.")
            journal = str(item.get("journal") or item.get("publisher") or "").strip()
            doi = str(item.get("doi") or "").strip()
            pieces = [title]
            if year and year != "n.d.":
                pieces.append(f"({year})")
            if journal:
                pieces.append(journal)
            if doi:
                pieces.append(f"DOI: {doi}")
            formatted = " — ".join(pieces) if len(pieces) > 1 else pieces[0]

    _save_citation(item, style or "APA", formatted, user_id=user_id)
