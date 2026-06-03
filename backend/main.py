import re
import os
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from .database import init_db, get_connection, get_today, normalize_citation
from .models import (
    PaperCreate, PaperUpdate, QueryRequest,
    ReferenceParseRequest, ReferenceBatchInsert,
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


# ---------------------------------------------------------------------------
# API: Tables & Query
# ---------------------------------------------------------------------------

@app.get("/api/tables")
def list_tables():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return {"tables": [r["name"] for r in rows]}


@app.post("/api/query")
def execute_query(req: QueryRequest):
    sql = req.sql.strip().rstrip(";")
    if not sql:
        raise HTTPException(400, "Empty query")

    upper = sql.lstrip().upper()
    is_select = upper.startswith("SELECT")
    is_update = upper.startswith("UPDATE")
    is_delete = upper.startswith("DELETE")

    if not (is_select or is_update or is_delete):
        raise HTTPException(400, "Only SELECT, UPDATE, and DELETE queries are allowed")

    if is_delete:
        if not re.search(r"\bWHERE\b", sql, re.IGNORECASE):
            raise HTTPException(400, "DELETE must include a WHERE clause")
        if not re.search(r"\bid\b", sql, re.IGNORECASE):
            raise HTTPException(400, "DELETE WHERE clause must filter by id (safety rule)")

    if is_update:
        if not re.search(r"\bWHERE\b", sql, re.IGNORECASE):
            raise HTTPException(400, "UPDATE must include a WHERE clause")
        if not re.search(r"\bid\b", sql, re.IGNORECASE):
            raise HTTPException(400, "UPDATE WHERE clause must filter by id (safety rule)")

    # --- Write queries (UPDATE / DELETE) ---
    if is_update or is_delete:
        try:
            with get_connection() as conn:
                cursor = conn.execute(sql)
                conn.commit()
                return {
                    "columns": ["rows_affected"],
                    "rows": [{"rows_affected": cursor.rowcount}],
                    "row_count": 1,
                    "total_count": 1,
                    "limited": False,
                }
        except Exception as e:
            raise HTTPException(400, str(e))

    # --- SELECT ---
    has_limit = bool(re.search(r"\bLIMIT\b", sql, re.IGNORECASE))

    total_count = None
    try:
        with get_connection() as conn:
            base = re.sub(r"\bLIMIT\s+\d+(\s+OFFSET\s+\d+)?\s*$", "", sql, flags=re.IGNORECASE).strip()
            total_count = conn.execute(f"SELECT COUNT(*) AS cnt FROM ({base})").fetchone()["cnt"]
    except Exception:
        pass

    has_order = bool(re.search(r"\bORDER\s+BY\b", sql, re.IGNORECASE))
    exec_sql = sql
    if not has_order and not has_limit:
        exec_sql += " ORDER BY id DESC"
    if not has_limit:
        exec_sql += " LIMIT 100"

    try:
        with get_connection() as conn:
            cursor = conn.execute(exec_sql)
            columns = [d[0] for d in cursor.description] if cursor.description else []
            rows = [dict(r) for r in cursor.fetchall()]
            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "total_count": total_count,
                "limited": not has_limit,
            }
    except Exception as e:
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------------------
# API: BibTeX parsing
# ---------------------------------------------------------------------------

@app.post("/api/bibtex/parse")
def parse_bibtex_endpoint(req: dict):
    bibtex = req.get("bibtex", "").strip()
    if not bibtex:
        raise HTTPException(400, "Empty BibTeX")

    fields = _parse_bibtex_fields(bibtex)
    if not fields:
        raise HTTPException(400, "Could not parse BibTeX entry")

    authors_parsed = _parse_bibtex_authors(fields.get("author", ""))
    title = fields.get("title", "")
    year = fields.get("year", "")
    url = fields.get("url") or fields.get("doi", "")
    if url and url.startswith("10."):
        url = f"https://doi.org/{url}"

    return {
        "title": title,
        "year": int(year) if year.isdigit() else None,
        "authors": ", ".join(f"{a['first']} {a['last']}" for a in authors_parsed),
        "paper_link": url,
        "abstract": fields.get("abstract", ""),
    }


def _parse_bibtex_fields(text: str) -> dict[str, str]:
    fields = {}
    # Handle key = {value} with one level of nested braces (e.g. {Teams of {LLM}})
    for m in re.finditer(r'(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}', text, re.DOTALL):
        fields[m.group(1).lower()] = re.sub(r"\s+", " ", m.group(2)).strip()
    # Handle key = "value" (common in ACL Anthology, Google Scholar exports)
    for m in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', text, re.DOTALL):
        key = m.group(1).lower()
        if key not in fields:
            fields[key] = re.sub(r"\s+", " ", m.group(2)).strip()
    # Strip LaTeX brace-protection from values ({LLM} -> LLM, {E}uropean -> European)
    fields = {k: re.sub(r'[{}]', '', v) for k, v in fields.items()}
    return fields


def _parse_bibtex_authors(raw: str) -> list[dict]:
    """Parse BibTeX author field into list of {'first': ..., 'last': ...}."""
    authors = []
    for part in re.split(r"\s+and\s+", raw):
        part = part.strip()
        if not part:
            continue
        if "," in part:
            pieces = part.split(",", 1)
            authors.append({"last": pieces[0].strip(), "first": pieces[1].strip()})
        else:
            words = part.split()
            if len(words) >= 2:
                authors.append({"last": words[-1], "first": " ".join(words[:-1])})
            else:
                authors.append({"last": words[0], "first": ""})
    return authors


# ---------------------------------------------------------------------------
# API: Papers CRUD
# ---------------------------------------------------------------------------

@app.get("/api/papers")
def list_papers():
    with get_connection() as conn:
        rows = conn.execute("SELECT id, title FROM paper_stats ORDER BY id DESC").fetchall()
        return {"papers": [dict(r) for r in rows]}


@app.get("/api/papers/{paper_id}")
def get_paper(paper_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM paper_stats WHERE id = ?", (paper_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Paper not found")
        result = dict(row)
        cites = conn.execute(
            "SELECT style, citation_text FROM paper_citation_format WHERE paper_id = ?", (paper_id,)
        ).fetchall()
        result["citations"] = {r["style"]: r["citation_text"] for r in cites}
        aliases = conn.execute(
            "SELECT alias_title FROM paper_aliases WHERE paper_id = ?", (paper_id,)
        ).fetchall()
        result["aliases"] = [r["alias_title"] for r in aliases]
        return result


@app.post("/api/papers")
def create_paper(paper: PaperCreate):
    today = get_today()
    with get_connection() as conn:
        try:
            cur = conn.execute(
                """INSERT INTO paper_stats
                   (title, year, labels, ref_count, cited_by_count, abstract, authors, paper_link, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (paper.title, paper.year, paper.labels, paper.ref_count,
                 paper.cited_by_count, paper.abstract, paper.authors,
                 paper.paper_link, today, today),
            )
            paper_id = cur.lastrowid
            _sync_labels(conn, paper_id, paper.labels)
            _sync_authors(conn, paper_id, paper.authors)
            _sync_citations(conn, paper_id, paper.citations)
            _sync_aliases(conn, paper_id, paper.aliases)
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(409, f"Paper already exists: {paper.title}")

    rematched = _rematch_unresolved_references()
    return {"id": paper_id, "message": "Paper created", "rematched": rematched}


@app.put("/api/papers/{paper_id}")
def update_paper(paper_id: int, paper: PaperUpdate):
    today = get_today()
    with get_connection() as conn:
        if not conn.execute("SELECT 1 FROM paper_stats WHERE id = ?", (paper_id,)).fetchone():
            raise HTTPException(404, "Paper not found")

        fields = {k: v for k, v in paper.model_dump(exclude={"citations", "aliases"}).items() if v is not None}
        if not fields and paper.citations is None and paper.aliases is None:
            return {"message": "No changes"}

        if fields:
            fields["updated_at"] = today
            set_clause = ", ".join(f"{k} = ?" for k in fields)
            values = list(fields.values()) + [paper_id]
            try:
                conn.execute(f"UPDATE paper_stats SET {set_clause} WHERE id = ?", values)
            except sqlite3.IntegrityError:
                raise HTTPException(409, "Duplicate paper title")

        if "labels" in fields:
            _sync_labels(conn, paper_id, fields["labels"])
        if "authors" in fields:
            _sync_authors(conn, paper_id, fields["authors"])
        if paper.citations is not None:
            _sync_citations(conn, paper_id, paper.citations)
        if paper.aliases is not None:
            _sync_aliases(conn, paper_id, paper.aliases)
        conn.commit()

    rematched = _rematch_unresolved_references()
    return {"message": "Paper updated", "rematched": rematched}


def _sync_labels(conn, paper_id: int, csv: str):
    conn.execute("DELETE FROM paper_labels WHERE paper_id = ?", (paper_id,))
    for label in csv.split(","):
        label = label.strip()
        if label:
            conn.execute("INSERT OR IGNORE INTO paper_labels (paper_id, label) VALUES (?,?)", (paper_id, label))


def _sync_authors(conn, paper_id: int, csv: str):
    conn.execute("DELETE FROM paper_authors WHERE paper_id = ?", (paper_id,))
    for name in csv.split(","):
        name = name.strip()
        if name:
            conn.execute("INSERT OR IGNORE INTO paper_authors (paper_id, author_name) VALUES (?,?)", (paper_id, name))


def _sync_aliases(conn, paper_id: int, aliases: list[str]):
    conn.execute("DELETE FROM paper_aliases WHERE paper_id = ?", (paper_id,))
    for alias in aliases:
        alias = alias.strip()
        if alias:
            conn.execute("INSERT OR IGNORE INTO paper_aliases (paper_id, alias_title) VALUES (?,?)", (paper_id, alias))


def _sync_citations(conn, paper_id: int, citations: dict[str, str]):
    conn.execute("DELETE FROM paper_citation_format WHERE paper_id = ?", (paper_id,))
    for style, text in citations.items():
        text = text.strip()
        if text:
            conn.execute(
                "INSERT OR IGNORE INTO paper_citation_format (paper_id, style, citation_text) VALUES (?,?,?)",
                (paper_id, style, text),
            )


# ---------------------------------------------------------------------------
# Matching engine: title-first, citation-format fallback
# ---------------------------------------------------------------------------

def _build_title_index(conn) -> list[tuple[int, str]]:
    """All (paper_id, title) pairs for substring matching, including aliases."""
    index = [(r["id"], r["title"]) for r in conn.execute("SELECT id, title FROM paper_stats").fetchall()]
    for r in conn.execute("SELECT paper_id, alias_title FROM paper_aliases").fetchall():
        index.append((r["paper_id"], r["alias_title"]))
    return index


def _build_citation_index(conn) -> dict[str, tuple[int, str]]:
    """Normalized-citation -> (paper_id, paper_title) lookup."""
    rows = conn.execute("""
        SELECT cf.citation_text, cf.paper_id, ps.title
        FROM paper_citation_format cf
        JOIN paper_stats ps ON ps.id = cf.paper_id
    """).fetchall()
    index = {}
    for r in rows:
        norm = normalize_citation(r["citation_text"])
        index[norm] = (r["paper_id"], r["title"])
    return index


def _match_reference(
    raw_text: str,
    title_index: list[tuple[int, str]],
    citation_index: dict[str, tuple[int, str]],
) -> tuple[int | None, str]:
    """Match a raw reference string against known papers.

    Strategy 1 (primary): check if any known paper title appears as a
    case-insensitive substring in the reference text.
    Strategy 2 (fallback): normalized citation-format matching.
    """
    raw_lower = raw_text.lower()

    # Strategy 1: title substring match (longest title first to avoid partial hits)
    for pid, title in sorted(title_index, key=lambda t: len(t[1]), reverse=True):
        if title.lower() in raw_lower:
            return pid, title

    # Strategy 2: citation format match
    norm = normalize_citation(raw_text)
    if norm in citation_index:
        return citation_index[norm]
    for stored_norm, (pid, title) in citation_index.items():
        if stored_norm in norm or norm in stored_norm:
            return pid, title

    return None, ""


def _rematch_unresolved_references() -> list[dict]:
    """Scan paper_reference rows where referenced_paper_id IS NULL and try to match them.

    Matching strategies (in order):
      1. Direct title lookup: if referenced_paper_title already set, look it up in paper_stats
      2. Title substring match against raw_citation_text
      3. Citation format match against raw_citation_text

    Returns a list of dicts describing each newly resolved reference.
    """
    matched_results = []
    with get_connection() as conn:
        title_index = _build_title_index(conn)
        citation_index = _build_citation_index(conn)
        # Map of lowered title -> (id, original title) for direct lookup
        title_lookup = {t.lower(): (pid, t) for pid, t in title_index}

        unresolved = conn.execute(
            """SELECT pr.id, pr.raw_citation_text, pr.referenced_paper_title,
                      pr.source_paper_id, ps.title AS source_title
               FROM paper_reference pr
               JOIN paper_stats ps ON ps.id = pr.source_paper_id
               WHERE pr.referenced_paper_id IS NULL"""
        ).fetchall()
        for ref in unresolved:
            pid, title = None, ""

            # Strategy 1a: exact title lookup (handles manual title edits via SQL)
            ref_title = (ref["referenced_paper_title"] or "").strip()
            if ref_title and ref_title.lower() in title_lookup:
                pid, title = title_lookup[ref_title.lower()]

            # Strategy 1b: substring match against referenced_paper_title
            if pid is None and ref_title:
                pid, title = _match_reference(ref_title, title_index, citation_index)

            # Strategy 2 & 3: match via raw_citation_text
            raw = (ref["raw_citation_text"] or "").strip()
            if pid is None and raw:
                pid, title = _match_reference(raw, title_index, citation_index)

            if pid is not None:
                conn.execute(
                    "UPDATE paper_reference SET referenced_paper_id = ?, referenced_paper_title = ? WHERE id = ?",
                    (pid, title, ref["id"]),
                )
                matched_results.append({
                    "reference_id": ref["id"],
                    "source_paper_title": ref["source_title"],
                    "matched_paper_title": title,
                    "matched_paper_id": pid,
                })
        conn.commit()
    return matched_results


@app.post("/api/references/rematch")
def rematch_endpoint():
    """Manually trigger re-matching of all unresolved references."""
    rematched = _rematch_unresolved_references()
    return {"rematched": rematched, "count": len(rematched)}


# ---------------------------------------------------------------------------
# API: Reference parsing & batch insert
# ---------------------------------------------------------------------------

@app.post("/api/references/parse")
def parse_references(req: ReferenceParseRequest):
    with get_connection() as conn:
        source = conn.execute("SELECT title FROM paper_stats WHERE id = ?", (req.source_paper_id,)).fetchone()
        if not source:
            raise HTTPException(404, "Source paper not found")

        title_index = _build_title_index(conn)
        citation_index = _build_citation_index(conn)
        existing_refs = {
            normalize_citation(r["raw_citation_text"])
            for r in conn.execute(
                "SELECT raw_citation_text FROM paper_reference WHERE source_paper_id = ?",
                (req.source_paper_id,),
            ).fetchall()
            if r["raw_citation_text"]
        }

    lines = _split_references(req.text)

    parsed = []
    for line in lines:
        pid, title = _match_reference(line, title_index, citation_index)
        norm = normalize_citation(line)
        parsed.append({
            "raw_citation_text": line,
            "referenced_paper_title": title,
            "referenced_paper_id": pid,
            "matched": pid is not None,
            "already_referenced": norm in existing_refs,
        })
    return {"source_paper_id": req.source_paper_id, "references": parsed}


def _split_references(text: str) -> list[str]:
    text = text.strip()
    # Strip a leading "References" / "Bibliography" header line
    text = re.sub(r"^(?:References|Bibliography)\s*\n", "", text, flags=re.IGNORECASE)

    # --- Phase 0: check for numbered styles BEFORE merging lines ---
    # Use \d{1,3} to avoid matching 4-digit years (2023., 2024.) as ref numbers
    # (?:^|\n) so the very first [1] at start-of-string is also captured
    parts = re.split(r"(?:^|\n)\s*\[(\d{1,3})\]\s*", text)
    if len(parts) > 2:
        return [re.sub(r"\s+", " ", s).strip() for s in _collect_parts(parts) if s.strip()]

    parts = re.split(r"(?:^|\n)\s*(\d{1,3})\.\s+", text)
    if len(parts) > 2:
        return [re.sub(r"\s+", " ", s).strip() for s in _collect_parts(parts) if s.strip()]

    # --- Phase 1: merge PDF line breaks ---
    raw_lines = text.split("\n")
    merged: list[str] = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if merged and _is_continuation(stripped, merged[-1]):
            prev = merged[-1]
            if prev.endswith("-") and not prev.endswith("--"):
                merged[-1] = prev[:-1] + stripped
            else:
                merged[-1] = prev + " " + stripped
        else:
            merged.append(stripped)

    # Post-process: fix URLs broken by line wraps
    result = []
    for s in merged:
        s = re.sub(r"\s+", " ", s).strip()
        s = s.replace("http s://", "https://").replace("http ://", "http://")
        if s:
            result.append(s)
    return result


_CONTINUATION_PREFIXES = re.compile(
    r"^(?:In |URL |Available |Accessed |Retrieved |Presented |Published |"
    r"Proceedings |Journal |Conference |Chapter |Technical |pp\.|vol\.|no\.)",
    re.IGNORECASE,
)


def _is_continuation(line: str, prev_line: str) -> bool:
    """Decide whether *line* is a continuation of *prev_line* rather than a new reference."""
    first = line[0] if line else ""

    # Starts with lowercase or URL-continuation chars -> definitely continuation
    if first.islower() or first in "./-":
        return True

    # Starts with a known venue / metadata prefix -> continuation
    if _CONTINUATION_PREFIXES.match(line):
        return True

    # Previous line didn't end with sentence-terminal punctuation -> still mid-sentence
    prev_stripped = prev_line.rstrip()
    prev_end = prev_stripped[-1] if prev_stripped else ""
    if prev_end not in (".", ")", "]"):
        return True

    # Previous line ends with a single-letter abbreviation (author initial like "D."
    # or "R.") -> the period is NOT a sentence ending, so this is still a continuation
    if re.search(r"\b[A-Z]\.$", prev_stripped):
        return True

    return False


def _collect_parts(parts: list[str]) -> list[str]:
    refs = []
    for i in range(1, len(parts), 2):
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if content:
            refs.append(content)
    return refs


@app.post("/api/references/batch")
def batch_insert_references(req: ReferenceBatchInsert):
    with get_connection() as conn:
        source = conn.execute("SELECT id, title FROM paper_stats WHERE id = ?", (req.source_paper_id,)).fetchone()
        if not source:
            raise HTTPException(404, "Source paper not found")

        title_lookup = {r["title"].lower(): r["id"] for r in conn.execute("SELECT id, title FROM paper_stats").fetchall()}
        alias_lookup = {r["alias_title"].lower(): r["paper_id"] for r in conn.execute("SELECT paper_id, alias_title FROM paper_aliases").fetchall()}

        inserted = skipped = 0
        for ref in req.references:
            raw = ref.get("raw_citation_text", "").strip()
            title = ref.get("referenced_paper_title", "").strip()
            pid = ref.get("referenced_paper_id")
            if not raw:
                continue
            if pid is None and title:
                key = title.lower()
                pid = title_lookup.get(key) or alias_lookup.get(key)
            try:
                conn.execute(
                    """INSERT INTO paper_reference
                       (source_paper_id, source_paper_title, referenced_paper_title, referenced_paper_id, raw_citation_text)
                       VALUES (?,?,?,?,?)""",
                    (source["id"], source["title"], title, pid, raw),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
        conn.commit()

    rematched = _rematch_unresolved_references()
    return {"inserted": inserted, "skipped_duplicates": skipped, "rematched": rematched}


# ---------------------------------------------------------------------------
# Static frontend
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
