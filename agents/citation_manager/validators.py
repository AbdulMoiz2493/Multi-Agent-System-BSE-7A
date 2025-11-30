import re
import requests
import time
from typing import Optional

CROSSREF_API = "https://api.crossref.org/works/"

# DOI syntax based on DOI Handbook recommendations
DOI_REGEX = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)

# Validate DOI string shape (accepts bare DOI; strips URL prefix)
def doi_syntax_is_valid(doi: str) -> bool:
    """Lightweight DOI syntax validation (no checksum exists for DOIs).
    Accepts forms like "10.xxxx/xxxxx". If a URL form is given, caller should
    normalize before validation. Returns True if string matches DOI pattern.
    """
    if not doi:
        return False
    doi = doi.strip()
    if doi.lower().startswith("http://doi.org/") or doi.lower().startswith("https://doi.org/"):
        doi = doi.split("doi.org/", 1)[-1]
    return bool(DOI_REGEX.match(doi))

# Check DOI is live via Crossref API (HTTP 200)
def verify_doi_live(doi: str, timeout: float = 3.0) -> bool:
    if not doi:
        return False
    doi = doi.strip()
    try:
        url = CROSSREF_API + doi
        r = requests.get(url, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False

# Fetch basic metadata from Crossref for a DOI
def fetch_metadata_from_doi(doi: str, timeout: float = 4.0) -> Optional[dict]:
    try:
        r = requests.get(CROSSREF_API + doi, timeout=timeout)
        if r.status_code != 200:
            return None
        data = r.json().get("message", {})
        md = {}
        md["title"] = data.get("title", [None])[0] if data.get("title") else None
        authors = []
        for a in data.get("author", [])[:10]:
            name = " ".join(filter(None, [a.get("given"), a.get("family")]))
            if name:
                authors.append(name)
        if authors:
            md["authors"] = authors
        md["year"] = None
        if data.get("published-print") and data["published-print"].get("date-parts"):
            md["year"] = data["published-print"]["date-parts"][0][0]
        elif data.get("published-online") and data["published-online"].get("date-parts"):
            md["year"] = data["published-online"]["date-parts"][0][0]
        md["journal"] = data.get("container-title", [None])[0]
        md["doi"] = doi
        md["url"] = data.get("URL")
        return md
    except Exception:
        return None

# Verify URL responds successfully (HEAD request, follow redirects)
def verify_url(url: str, timeout: float = 3.0) -> bool:
    try:
        r = requests.head(url, timeout=timeout, allow_redirects=True)
        return 200 <= r.status_code < 400
    except Exception:
        return False

# Enrich metadata by bibliographic search (Crossref top result)
def search_metadata_bibliographic(query: str, timeout: float = 4.5) -> Optional[dict]:
    """Search CrossRef by a free-form bibliographic string and return best‑match metadata.

    This helps when a DOI is not present in the raw text: we can still enrich
    title, authors, year, journal, DOI, and URL from the top result.
    """
    try:
        if not query or len(query.strip()) < 40:
            return None
        params = {
            "query.bibliographic": query.strip(),
            "rows": 1,
        }
        r = requests.get("https://api.crossref.org/works", params=params, timeout=timeout)
        if r.status_code != 200:
            return None
        items = (r.json() or {}).get("message", {}).get("items", [])
        if not items:
            return None
        data = items[0]
        md = {}
        title_list = data.get("title") or []
        md["title"] = title_list[0] if title_list else None
        authors = []
        for a in (data.get("author") or [])[:10]:
            name = " ".join(filter(None, [a.get("given"), a.get("family")]))
            if name:
                authors.append(name)
        if authors:
            md["authors"] = authors
        md["year"] = None
        if data.get("published-print") and data["published-print"].get("date-parts"):
            md["year"] = data["published-print"]["date-parts"][0][0]
        elif data.get("published-online") and data["published-online"].get("date-parts"):
            md["year"] = data["published-online"]["date-parts"][0][0]
        md["journal"] = (data.get("container-title") or [None])[0]
        md["doi"] = data.get("DOI")
        md["url"] = data.get("URL")
        return md
    except Exception:
        return None
