# Vibe Prompts

All prompts used to generate this paper database project.

---

## Prompt 1 — Initial Design & Scaffolding

```
in this repo, I need to build a lite database to store
paper_stats table: 
paper title, year of publish, labels (keywords separated by ","), number of paper it referenced, number of paper it is referenced, abstract, authors, paper link

paper_reference table:
paper title, id in paper_stats, paper title it references. id in paper_stats

a simple UI
searching mode
1. i can select which table to view (in side bar), and showing table data, but only the first 100 rows by default (also showing total number of rows available)
2. a text entering window, I can enter sql and be parsed to refresh data shown (also showing total number of rows available, if 0, then show 0 rows)

another simple UI 
filling mode
(have a button to switch between searching mode and filling mode)
(i need either a survey like page to fill or something alike)
1. i need to filling tables paper_stats directly (e.g. i found an interesting paper, i copied key info from google scholar, and axiv abstract web page)
2. i need to batch insert references of a paper in  paper_stats into paper_reference (e.g. after step 1, i will copy and paste the reference paragraph from the paper, and then my api backend parse them into lines fit into paper_reference, and then highlight me those paper not already in paper_stats base on paper name (exact match for current version of design), then I can build a paper reference network)

critique my design, tell me what dependencies I need, then
add .gitignore
add vibe_prompt.md in E:\git_fork_folder\paper_db\vibe_prompt, and store all promtp I used to generate this DB
```

---

## Prompt 2 — Design Feedback & Full Build

```
paper_stats  issue 1: then we need a paper label table, and in future, we can have a concatenated UI page to show overview result filtered by complex sql logic at runtime

paper_stats issue 2: you are right, only keep static total reference count from the original paper just for reference (the paper may update)

paper_stats issue 3: just "id" would be enough?

paper_stats issue 4: you are right, add such table, but will need the filling UI to update those related tables together

paper_stats issue 5: you are right, add them, with format, yyyyMMdd from system time, it would be enough to use without hours, minute or seconds

paper_reference issue 1: I still want them to both exist, or in future, we have a better UI page, it use more sql to filter results I want now

paper_reference issue 2: yes, you are right

paper_reference issue 3: you are right, so in paper_stats, we also need a unique key, so we dont add duplicate papers

UI: Searching Mode: i was expecting just a normal sql querying page, when no limit keyword is added, then it is automaticly added. If user specified limit 300, then it shows all 300 rows (user need to scroll down, the page shows for example at most 30 lines in one screen)

UI: Filling Mode: I want the DB to be started at local, and stored inside this repo (the size is very limited, I only store paper match my interest in a small field); So there woud be no network bottleneck

Your recm is good for the tech stack, I would prefer both a native UI or a UI can be visited from Chrome to local host port

I would also need you to have a startup script run_server.sh for example to start the server, and ctrl+C to wait for any workflow in process to finish, and save the DB, then stop everything

you may use a venv, to make this repo portable
```

---

## Prompt 3 — Port Change

```
I wnat to use a less conflicted port 16666 instead of 8000
```

---

## Prompt 4 — Citation-Based Matching (replacing regex title extraction)

```
add a paper_citation_text (or better names) table (to be filled when inserting into fill page, include all reference styles IEEE, Harverd and etc.)
now for the reference table, I dont need you to extract the title, i need you to exact match those in paper_citation_text table, then you can link to the paper_stats, and then obtain the paper title

I believe now papers provide citations, then citations across different papers are consistent

Potential issues to flag
1. yes you are right, use what you recommended [normalized matching: collapse whitespace, lowercase, strip punctuation]
2. then do that for by-ways, when filling the references, update the matching; when filing in a new paper into paper_stats, do the matching and updating another time
3. yes i will, in the filling page, give me more text windows to fill different citation styles
```

---

## Prompt 5 — PDF line-break handling & title-based matching

```
issue 1: reference style in two columns are not correctly identified due to pdf new line
(PDF copy-paste creates spurious line breaks mid-word/mid-sentence from two-column layout)

issue 2: citation format exact matching doesn't work because pasted reference text differs from stored citation formats.
Solution: match by paper title as a substring within the reference text instead.
Iterate all paper titles for each match - small scale DB makes this feasible.

Also: auto-fill citation formats from BibTeX, and show re-match results on fill page.
```

---

## Prompt 6 — Simplify citation storage

```
Since matching is now title-based, multiple citation styles (APA, IEEE, Harvard, MLA) are unnecessary.
Decision: keep only BibTeX field + auto-fill (extracts title, year, authors, link from BibTeX).
Removed APA/IEEE/Harvard/MLA textareas from the form.
```

---

## Prompt 7 — Reference splitter bugs & test suite

**Blockers encountered:**
1. `\d+` in split regex matched 4-digit years (2023, 2024) as reference numbers → only 4 "references" returned.
   Fix: use `\d{1,3}` to exclude years.
2. Author abbreviations like `Kang, D.` end with `.`, so the next line (paper title) was split as a new reference.
   Fix: detect single-letter abbreviation endings (`\b[A-Z]\.$`) and treat next line as continuation.
3. Lines starting with `In` (venue prefix, e.g. "In International Conference on...") incorrectly treated as new references.
   Fix: added `_CONTINUATION_PREFIXES` list (In, URL, Proceedings, Journal, Conference, etc.).
4. `[1]` at start of string had no `\n` before it, so first reference was lost in numbered-style splitting.
   Fix: changed regex to `(?:^|\n)\s*\[(\d{1,3})\]`.

**Test file:** `test/reference_listParsing_test.py` — 6 test cases with debug tracing on failure.

---

## Prompt 8 — UI polish & usability

```
Choices made:
- Search mode: added flex layout constraints (min-height: 0, flex-shrink: 0) so table scrolls within viewport.
- Fill mode: same scroll fix applied.
- SQL UPDATE/DELETE allowed in search mode, but must include WHERE clause filtering by id (safety rule).
- Title mismatch across paper versions (e.g. "database" vs "Dataset") accepted as known limitation of exact matching.
  Workaround: manually update title after auto-match, then re-match.
- Re-match button added to sidebar: triggers _rematch_unresolved_references() on demand.
  Also updated re-match to check referenced_paper_title directly against paper_stats.title (handles manual SQL edits).
- Paper dropdowns replaced with searchable select: type [id] or partial title to filter, 10 visible items with scroll, 300ms debounce.

Future feature (deferred):
- Network/graph view using Cytoscape.js — nodes = papers (sized by in-degree), edges = citations (directed arrows),
  color-coded by year, dagre layout. Schema already supports this, no changes needed.
```
