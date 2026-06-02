# Paper DB

A lightweight local database for managing academic papers, their metadata, and reference networks. Built with Python (FastAPI + SQLite) and a browser-based UI.

## Quick Start

**Windows:**
```
run_server.bat
```

**Linux / macOS / Git Bash:**
```bash
chmod +x run_server.sh
./run_server.sh
```

Then open **http://127.0.0.1:16666** in your browser. Press `Ctrl+C` to stop the server.

The startup script automatically creates a Python virtual environment (`.venv/`) and installs dependencies on first run.

## Schema

| Table | Purpose |
|-------|---------|
| `paper_stats` | Core paper metadata (title, year, authors, labels, abstract, link, ref counts, timestamps) |
| `paper_labels` | Normalized label/keyword lookup (one row per paper-label pair) |
| `paper_authors` | Normalized author lookup (one row per paper-author pair) |
| `paper_aliases` | Alternate titles for a paper, used during reference matching |
| `paper_citation_format` | Stored citation text per style (e.g. BibTeX) for a paper |
| `paper_reference` | Directed reference edges between papers (`raw_citation_text` + matched IDs) |

## UI Modes

### Search Mode
- Select a table from the sidebar to browse its contents
- Write arbitrary `SELECT` / `UPDATE` / `DELETE` queries in the SQL editor (Ctrl+Enter to execute)
- Auto-applies `LIMIT 100` when no LIMIT clause is present; shows total row count
- `UPDATE` / `DELETE` require a `WHERE id = ...` clause for safety

### Fill Mode
- **Add / Edit Paper** — form to insert or update `paper_stats` (also syncs labels, authors, aliases, and BibTeX)
- **BibTeX Auto-fill** — paste a BibTeX entry to auto-populate title, year, authors, link, and abstract
- **Alternate Titles** — register variant names for a paper so references using different titles still match
- **Batch References** — paste a reference section, parse it into individual entries, see which papers are already in the DB, then batch-insert into `paper_reference`
- **Reference Matching** — on insert, references are auto-matched against paper titles, aliases, and citation formats; a sidebar "Re-match References" button re-scans all unresolved references

## Reference Matching Strategy

When a reference is inserted or re-matched, the system tries (in order):

1. **Direct title lookup** — if `referenced_paper_title` is set, exact match against `paper_stats.title` and `paper_aliases.alias_title`
2. **Title substring match** — check if any known title (including aliases) appears as a case-insensitive substring in the raw citation text
3. **Citation format match** — normalized matching against stored citation texts in `paper_citation_format`

## Tech Stack

- **Backend:** Python, FastAPI, SQLite (stdlib `sqlite3`)
- **Frontend:** Vanilla HTML / CSS / JS (served as static files)
- **Server:** Uvicorn

## Project Structure

```
paper_db/
├── backend/          # FastAPI application
│   ├── main.py       # Routes, API endpoints, matching engine
│   ├── database.py   # SQLite setup and connection helpers
│   └── models.py     # Pydantic request/response models
├── static/           # Frontend (served at /)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── data/             # SQLite database file (auto-created, tracked in git)
├── test/             # Tests for reference parsing, BibTeX parsing
├── vibe_prompt/      # Prompts used to generate this project
├── requirements.txt
├── run_server.sh     # Linux/macOS startup
└── run_server.bat    # Windows startup
```
