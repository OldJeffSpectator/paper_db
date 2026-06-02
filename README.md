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
| `paper_reference` | Directed reference edges between papers |

## UI Modes

### Search Mode
- Select a table from the sidebar to browse its contents
- Write arbitrary `SELECT` queries in the SQL editor (Ctrl+Enter to execute)
- Auto-applies `LIMIT 100` when no LIMIT clause is present; shows total row count

### Fill Mode
- **Add / Edit Paper** — form to insert or update `paper_stats` (also syncs `paper_labels` and `paper_authors`)
- **Batch References** — paste a reference section, parse it into individual entries, see which papers are already in the DB, then batch-insert into `paper_reference`

## Tech Stack

- **Backend:** Python, FastAPI, SQLite (stdlib `sqlite3`)
- **Frontend:** Vanilla HTML / CSS / JS (served as static files)
- **Server:** Uvicorn

## Project Structure

```
paper_db/
├── backend/          # FastAPI application
│   ├── main.py       # Routes and API endpoints
│   ├── database.py   # SQLite setup and connection helpers
│   └── models.py     # Pydantic request/response models
├── static/           # Frontend (served at /)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── data/             # SQLite database file (auto-created)
├── vibe_prompt/      # Prompts used to generate this project
├── requirements.txt
├── run_server.sh     # Linux/macOS startup
└── run_server.bat    # Windows startup
```
