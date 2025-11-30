import os
from typing import Dict, Any, List, Optional

try:
    from citeproc import CitationStylesStyle, Citation, CitationItem, CitationStylesBibliography
    from citeproc.source.json import CiteProcJSON
    from citeproc import formatter
    CITEPROC_AVAILABLE = True
except Exception:
    CITEPROC_AVAILABLE = False


STYLE_FILE_MAP = {
    "apa": ["apa.csl"],
    "mla": ["mla.csl", "modern-language-association.csl", "modern-language-association (1).csl"],
    "chicago": ["chicago-author-date.csl", "chicago-note-bibliography.csl", "chicago.csl"],
    "harvard": ["harvard.csl", "harvard-cite-them-right.csl"],
    "ieee": ["ieee.csl"],
}


# Resolve CSL style file path from env or local styles
def _style_path(style_key: str) -> str:
    style_key = (style_key or "apa").strip().lower()
    filename = STYLE_FILE_MAP.get(style_key)
    if not filename:
        # default to APA
        filename = STYLE_FILE_MAP["apa"]
    base_dir = os.environ.get("CSL_STYLE_DIR", os.path.join("agents", "citation_manager", "csl"))
    return os.path.join(base_dir, filename)


def _split_name(full_name: str) -> Dict[str, str]:
    parts = [p for p in (full_name or "").strip().split() if p]
    if not parts:
        return {"literal": full_name or ""}
    if len(parts) == 1:
        return {"family": parts[0]}
    return {"given": " ".join(parts[:-1]), "family": parts[-1]}


# Map normalized citation item to CSL-JSON fields
def map_to_csl_json(item: Dict[str, Any], source_type: Optional[str] = None, include_doi: bool = True) -> Dict[str, Any]:
    """Map normalized engine item to CSL-JSON structure."""
    typemap = {
        "article": "article-journal",
        "book": "book",
        "web": "webpage",
    }
    csl: Dict[str, Any] = {
        "id": item.get("id") or item.get("doi") or item.get("url") or "item-1",
        "type": typemap.get((source_type or "article").lower(), "article-journal"),
        "title": item.get("title") or "",
        "author": [],
    }
    authors: List[str] = item.get("authors") or ([] if not item.get("author") else [item.get("author")])
    mapped_authors = [_split_name(a) for a in authors]
    if not mapped_authors:
        mapped_authors = [{"literal": "Unknown"}]
    csl["author"] = mapped_authors

    year = item.get("year")
    if year:
        try:
            y = int(str(year).strip())
            csl["issued"] = {"date-parts": [[y]]}
        except Exception:
            pass

    # Container metadata
    if item.get("journal"):
        csl["container-title"] = item.get("journal")
    if item.get("volume"):
        csl["volume"] = str(item.get("volume"))
    if item.get("issue"):
        csl["issue"] = str(item.get("issue"))
    if item.get("pages"):
        csl["page"] = str(item.get("pages"))
    if item.get("publisher"):
        csl["publisher"] = item.get("publisher")

    doi = item.get("doi")
    if include_doi and doi:
        csl["DOI"] = str(doi).replace("https://doi.org/", "").strip()
    url = item.get("url")
    if url:
        csl["URL"] = url

    return csl


# Render a single citation using CSL style files
def format_with_csl(style: str, item: Dict[str, Any], source_type: Optional[str] = None, include_doi: bool = True) -> str:
    """Render a single citation using CSL if available and style file exists.
    Returns a plain text citation string.
    """
    if not CITEPROC_AVAILABLE:
        raise RuntimeError("citeproc-py not installed")

    style_path = _style_path(style)
    if not os.path.exists(style_path):
        raise FileNotFoundError(f"CSL style file not found: {style_path}")

    try:
        csl_item = map_to_csl_json(item, source_type=source_type, include_doi=include_doi)
        source = CiteProcJSON([csl_item])
        csl_style = CitationStylesStyle(style_path, validate=False)
        bibliography = CitationStylesBibliography(csl_style, source, formatter.plain)
        citation = Citation([CitationItem(csl_item["id"])])
        bibliography.register(citation)
        rendered = bibliography.bibliography()
        return str(rendered[0]) if rendered else ""
    except Exception:
        authors = item.get("authors") or ([] if not item.get("author") else [item.get("author")])
        author_str = ", ".join(authors) if authors else "Unknown"
        year = str(item.get("year") or "n.d.")
        title = (item.get("title") or "").strip()
        journal = (item.get("journal") or item.get("publisher") or "").strip()
        vol = str(item.get("volume") or "").strip()
        iss = str(item.get("issue") or "").strip()
        pages = str(item.get("pages") or "").strip()
        doi = item.get("doi")
        url = item.get("url")
        parts: List[str] = []
        if author_str:
            parts.append(author_str)
        if year:
            parts.append(year)
        if title:
            parts.append(title)
        if journal:
            parts.append(journal)
        vol_iss = "".join([
            f"{vol}" if vol else "",
            f"({iss})" if iss else ""
        ])
        if vol_iss:
            parts.append(vol_iss)
        if pages:
            parts.append(pages)
        tail = doi and f"https://doi.org/{str(doi).replace('https://doi.org/','').strip()}" or url or ""
        if tail:
            parts.append(tail)
        return ". ".join([p for p in parts if p])


# Render a bibliography string from multiple items via CSL
def format_bibliography_with_csl(style: str, items: List[Dict[str, Any]], include_doi: bool = True) -> str:
    """Render a list of citations as a bibliography using CSL.
    Returns newline-separated string entries.
    """
    if not CITEPROC_AVAILABLE:
        raise RuntimeError("citeproc-py not installed")

    style_path = _style_path(style)
    if not os.path.exists(style_path):
        raise FileNotFoundError(f"CSL style file not found: {style_path}")

    csl_items: List[Dict[str, Any]] = []
    for idx, it in enumerate(items):
        csl_items.append(map_to_csl_json(it, source_type=it.get("source_type"), include_doi=include_doi))

    try:
        source = CiteProcJSON(csl_items)
        csl_style = CitationStylesStyle(style_path, validate=False)
        bibliography = CitationStylesBibliography(csl_style, source, formatter.plain)

        for ci in csl_items:
            citation = Citation([CitationItem(ci["id"])])
            bibliography.register(citation)

        rendered = bibliography.bibliography()
        return "\n".join([str(entry) for entry in rendered])
    except Exception:
        def _fmt_min(it: Dict[str, Any]) -> str:
            authors = it.get("authors") or ([] if not it.get("author") else [it.get("author")])
            author_str = ", ".join(authors) if authors else "Unknown"
            year = str(it.get("year") or "n.d.")
            title = (it.get("title") or "").strip()
            journal = (it.get("journal") or it.get("publisher") or "").strip()
            vol = str(it.get("volume") or "").strip()
            iss = str(it.get("issue") or "").strip()
            pages = str(it.get("pages") or "").strip()
            doi = it.get("doi")
            url = it.get("url")
            parts: List[str] = []
            if author_str:
                parts.append(author_str)
            if year:
                parts.append(year)
            if title:
                parts.append(title)
            if journal:
                parts.append(journal)
            vol_iss = "".join([
                f"{vol}" if vol else "",
                f"({iss})" if iss else ""
            ])
            if vol_iss:
                parts.append(vol_iss)
            if pages:
                parts.append(pages)
            tail = doi and f"https://doi.org/{str(doi).replace('https://doi.org/','').strip()}" or url or ""
            if tail:
                parts.append(tail)
            return ". ".join([p for p in parts if p])

        return "\n".join(_fmt_min(it) for it in items)


# Re-define _style_path to support external styles directory via CSL_STYLE_DIR
def _style_path(style: str) -> str:
    """Resolve CSL style file path, supporting common filename variants.

    Checks `CSL_STYLE_DIR` first, then local `agents/citation_manager/csl/`.
    """
    style_key = (style or "APA").strip().lower()
    candidates = STYLE_FILE_MAP.get(style_key, [f"{style_key}.csl"]) 

    def resolve_in_dir(dir_path: str) -> Optional[str]:
        for name in candidates:
            p = os.path.join(dir_path, name)
            if os.path.exists(p):
                return p
        try:
            names = [n for n in os.listdir(dir_path) if n.endswith(".csl")]
            tokens_map = {
                "mla": ["mla", "modern-language-association"],
                "chicago": ["chicago", "author-date", "note-bibliography"],
                "harvard": ["harvard", "cite-them-right"],
                "apa": ["apa"],
                "ieee": ["ieee"],
            }
            tokens = tokens_map.get(style_key, [style_key])
            for n in names:
                ln = n.lower()
                if any(t in ln for t in tokens):
                    return os.path.join(dir_path, n)
        except Exception:
            pass
        return None

    style_dir_env = os.environ.get("CSL_STYLE_DIR")
    if style_dir_env:
        resolved = resolve_in_dir(style_dir_env)
        if resolved:
            return resolved

    local_dir = os.path.join(os.path.dirname(__file__), "csl")
    resolved = resolve_in_dir(local_dir)
    if resolved:
        return resolved

    return os.path.join(local_dir, candidates[0])
