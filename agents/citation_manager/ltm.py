import sqlite3
import json
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "citation_ltm.db"

# Ensure local SQLite DB and schema exist (incl. optional user_id)
def _ensure_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS citations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doi TEXT,
            title TEXT,
            authors TEXT,
            style TEXT,
            formatted TEXT,
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_id TEXT
        )
        """
    )
    conn.commit()
    try:
        c.execute("PRAGMA table_info(citations)")
        cols = [row[1] for row in c.fetchall()]
        if "user_id" not in cols:
            c.execute("ALTER TABLE citations ADD COLUMN user_id TEXT")
            conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

# Save a formatted citation and its metadata to LTM
def save_citation(item: dict, style: str, formatted: str, user_id: Optional[str] = None):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    doi = item.get("doi")
    title = item.get("title")
    authors = json.dumps(item.get("authors") or [])
    metadata = json.dumps(item)
    c.execute(
        """
        INSERT INTO citations (doi, title, authors, style, formatted, metadata, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (doi, title, authors, style, formatted, metadata, user_id),
    )
    conn.commit()
    conn.close()

# Query most recent citations (basic fields and timestamp)
def query_recent(limit: int = 20):
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, doi, title, authors, style, formatted, created_at FROM citations ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# Check for existing citation by DOI or title (case-insensitive)
def exists_duplicate(doi: Optional[str] = None, title: Optional[str] = None) -> bool:
    """Return True if a citation with the same DOI or title already exists.
    Comparison is case-insensitive and trims whitespace. If both provided,
    match either condition.
    """
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        if doi:
            doi_norm = (doi or "").strip().lower()
            c.execute("SELECT 1 FROM citations WHERE LOWER(TRIM(doi)) = ? LIMIT 1", (doi_norm,))
            if c.fetchone():
                return True
        if title:
            title_norm = (title or "").strip().lower()
            c.execute("SELECT 1 FROM citations WHERE LOWER(TRIM(title)) = ? LIMIT 1", (title_norm,))
            if c.fetchone():
                return True
        return False
    finally:
        conn.close()


# Search citations with filters and simple relevance sorting
def search_citations(
    user_id: Optional[str] = None,
    query: Optional[str] = None,
    style: Optional[str] = None,
    limit: int = 50,
    since: Optional[str] = None,
    until: Optional[str] = None,
):
    """Retrieve citations with optional filters and simple personalization.

    - Filters by user_id if provided.
    - Performs simple LIKE-based search across title, formatted, and metadata.
    - Filters by style and created_at range if provided.
    - Returns list of dict rows.
    """
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    conditions = []
    params = []
    if user_id:
        conditions.append("user_id = ?")
        params.append(user_id)
    if style:
        conditions.append("LOWER(style) = LOWER(?)")
        params.append(style)
    if since:
        conditions.append("created_at >= ?")
        params.append(since)
    if until:
        conditions.append("created_at <= ?")
        params.append(until)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    base_query = f"SELECT id, doi, title, authors, style, formatted, metadata, created_at, user_id FROM citations {where_clause} ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    c.execute(base_query, tuple(params))
    rows = [dict(row) for row in c.fetchall()]
    conn.close()

    if query:
        q = (query or "").strip().lower()
        def score(row):
            s = 0
            for field in (row.get("title") or "", row.get("formatted") or "", row.get("metadata") or ""):
                s += (field.lower().count(q))
            if user_id and row.get("user_id") == user_id:
                s += 1
            return s
        rows.sort(key=lambda r: (score(r), r.get("created_at")), reverse=True)

    for r in rows:
        try:
            r["authors"] = json.loads(r.get("authors") or "[]")
        except Exception:
            r["authors"] = []
        try:
            r["metadata"] = json.loads(r.get("metadata") or "{}")
        except Exception:
            r["metadata"] = {}
        try:
            if isinstance(r.get("metadata"), dict):
                rt = r["metadata"].get("raw_text") or r["metadata"].get("source_text")
                if rt:
                    r["raw_text"] = rt
        except Exception:
            pass

    return rows
