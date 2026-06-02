import re
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "paper_db.sqlite")


def get_today() -> str:
    return datetime.now().strftime("%Y%m%d")


@contextmanager
def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS paper_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                year INTEGER,
                labels TEXT DEFAULT '',
                ref_count INTEGER DEFAULT 0,
                cited_by_count INTEGER DEFAULT 0,
                abstract TEXT DEFAULT '',
                authors TEXT DEFAULT '',
                paper_link TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS paper_labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                FOREIGN KEY (paper_id) REFERENCES paper_stats(id) ON DELETE CASCADE,
                UNIQUE(paper_id, label)
            );

            CREATE TABLE IF NOT EXISTS paper_authors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                FOREIGN KEY (paper_id) REFERENCES paper_stats(id) ON DELETE CASCADE,
                UNIQUE(paper_id, author_name)
            );

            CREATE TABLE IF NOT EXISTS paper_citation_format (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL,
                style TEXT NOT NULL,
                citation_text TEXT NOT NULL,
                FOREIGN KEY (paper_id) REFERENCES paper_stats(id) ON DELETE CASCADE,
                UNIQUE(paper_id, style)
            );

            CREATE TABLE IF NOT EXISTS paper_reference (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_paper_id INTEGER NOT NULL,
                source_paper_title TEXT NOT NULL,
                referenced_paper_title TEXT NOT NULL DEFAULT '',
                referenced_paper_id INTEGER,
                raw_citation_text TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (source_paper_id) REFERENCES paper_stats(id) ON DELETE CASCADE,
                FOREIGN KEY (referenced_paper_id) REFERENCES paper_stats(id) ON DELETE SET NULL,
                UNIQUE(source_paper_id, raw_citation_text)
            );
        """)
        conn.commit()


def normalize_citation(text: str) -> str:
    """Normalize a citation string for matching: lowercase, collapse whitespace, strip punctuation edges."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = text.strip(".,;: ")
    return text
