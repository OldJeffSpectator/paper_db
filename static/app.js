// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let currentMode = "search";
let currentTable = "";
let fillTab = "paper";
let editingPaperId = null;


// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
async function api(method, url, body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

function $(id) { return document.getElementById(id); }

function showMsg(elId, text, ok) {
  const el = $(elId);
  el.textContent = text;
  el.className = "msg " + (ok ? "ok" : "err");
  setTimeout(() => { el.className = "msg"; }, 5000);
}

function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ---------------------------------------------------------------------------
// Mode switching
// ---------------------------------------------------------------------------
function switchMode(mode) {
  currentMode = mode;
  $("btn-search").classList.toggle("active", mode === "search");
  $("btn-fill").classList.toggle("active", mode === "fill");
  $("btn-graph").classList.toggle("active", mode === "graph");
  $("search-mode").style.display = mode === "search" ? "" : "none";
  $("fill-mode").style.display   = mode === "fill"   ? "" : "none";
  $("graph-mode").style.display  = mode === "graph"  ? "" : "none";
  $("sidebar-tables").style.display = mode === "graph" ? "none" : "";
  $("sidebar-graph").style.display  = mode === "graph" ? "" : "none";
  if (mode === "fill") refreshPaperDropdowns();
  if (mode === "graph") loadGraph();
}

function switchFillTab(tab) {
  fillTab = tab;
  $("tab-paper").classList.toggle("active", tab === "paper");
  $("tab-refs").classList.toggle("active", tab === "refs");
  $("paper-section").style.display = tab === "paper" ? "" : "none";
  $("refs-section").style.display  = tab === "refs"  ? "" : "none";
  if (tab === "refs") {
    $("ref-paper-input").value = "";
    $("ref-paper-select").value = "";
  }
}

// ---------------------------------------------------------------------------
// Search mode: tables list
// ---------------------------------------------------------------------------
async function loadTables() {
  const { tables } = await api("GET", "/api/tables");
  const ul = $("table-list");
  ul.innerHTML = "";
  tables.forEach(t => {
    const li = document.createElement("li");
    li.textContent = t;
    li.onclick = () => selectTable(t);
    ul.appendChild(li);
  });
  if (tables.length) selectTable(tables.includes("paper_stats") ? "paper_stats" : tables[0]);
}

function selectTable(name) {
  currentTable = name;
  document.querySelectorAll("#table-list li").forEach(li => {
    li.classList.toggle("active", li.textContent === name);
  });
  api("POST", "/api/query", { sql: `SELECT * FROM ${name} ORDER BY id DESC` })
    .then(data => renderResults(data))
    .catch(e => {
      $("result-info").textContent = "Error: " + e.message;
      $("results-head").innerHTML = "";
      $("results-body").innerHTML = "";
    });
}

// ---------------------------------------------------------------------------
// Search mode: execute query
// ---------------------------------------------------------------------------
async function executeQuery() {
  const el = $("sql-input");
  const selected = el.value.substring(el.selectionStart, el.selectionEnd).trim();
  const sql = selected || el.value.trim();
  if (!sql) return;
  try {
    const data = await api("POST", "/api/query", { sql });
    renderResults(data);
  } catch (e) {
    $("result-info").textContent = "Error: " + e.message;
    $("results-head").innerHTML = "";
    $("results-body").innerHTML = "";
  }
}

function renderResults(data) {
  const { columns, rows, row_count, total_count, limited } = data;

  let info = `Showing ${row_count} row${row_count !== 1 ? "s" : ""}`;
  if (total_count !== null && total_count !== undefined) {
    info += ` of ${total_count} total`;
  }
  if (limited) info += " (LIMIT 100 auto-applied)";
  $("result-info").textContent = info;

  const thead = $("results-head");
  thead.innerHTML = "<tr>" + columns.map(c => `<th>${esc(c)}</th>`).join("") + "</tr>";

  const tbody = $("results-body");
  tbody.innerHTML = rows.map(r =>
    "<tr>" + columns.map(c => `<td title="${esc(String(r[c] ?? ""))}">${esc(String(r[c] ?? ""))}</td>`).join("") + "</tr>"
  ).join("");
}

// ---------------------------------------------------------------------------
// Searchable select component
// ---------------------------------------------------------------------------
let allPapers = [];

function initSearchableSelect(inputId, hiddenId, listId, onSelect) {
  const input = $(inputId);
  const hidden = $(hiddenId);
  const list = $(listId);
  let debounceTimer = null;

  input.addEventListener("focus", () => {
    renderSSList(listId, input.value.trim());
    list.classList.add("open");
  });

  input.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      renderSSList(listId, input.value.trim());
      list.classList.add("open");
    }, 300);
  });

  document.addEventListener("click", (e) => {
    if (!input.contains(e.target) && !list.contains(e.target)) {
      list.classList.remove("open");
    }
  });

  list.addEventListener("click", (e) => {
    const li = e.target.closest("li");
    if (!li || li.classList.contains("ss-no-results")) return;
    const id = li.dataset.id;
    const label = li.textContent;
    hidden.value = id;
    input.value = label;
    list.classList.remove("open");
    if (onSelect) onSelect(id);
  });
}

function renderSSList(listId, query) {
  const list = $(listId);
  const q = query.toLowerCase();
  const filtered = allPapers.filter(p => {
    if (!q) return true;
    const label = `[${p.id}] ${p.title}`.toLowerCase();
    return label.includes(q);
  });

  list.innerHTML = "";
  if (filtered.length === 0) {
    list.innerHTML = '<li class="ss-no-results">No matches</li>';
    return;
  }
  filtered.forEach(p => {
    const li = document.createElement("li");
    li.dataset.id = p.id;
    li.textContent = `[${p.id}] ${p.title}`;
    list.appendChild(li);
  });
}

// ---------------------------------------------------------------------------
// Fill mode: paper dropdowns
// ---------------------------------------------------------------------------
async function refreshPaperDropdowns() {
  const { papers } = await api("GET", "/api/papers");
  allPapers = papers;
  renderSSList("edit-paper-list", $("edit-paper-input").value.trim());
  renderSSList("ref-paper-list", $("ref-paper-input").value.trim());
}

// ---------------------------------------------------------------------------
// Fill mode: load paper for edit (including citations)
// ---------------------------------------------------------------------------
async function loadPaperForEdit(id) {
  if (!id) {
    resetPaperForm();
    return;
  }
  try {
    const p = await api("GET", `/api/papers/${id}`);
    editingPaperId = p.id;
    $("f-title").value    = p.title || "";
    $("f-year").value     = p.year  || "";
    $("f-authors").value  = p.authors || "";
    $("f-labels").value   = p.labels || "";
    $("f-refcount").value = p.ref_count || 0;
    $("f-citedby").value  = p.cited_by_count || 0;
    $("f-abstract").value = p.abstract || "";
    $("f-link").value     = p.paper_link || "";

    $("f-cite-bibtex").value = (p.citations || {}).BibTeX || "";
    $("f-aliases").value = (p.aliases || []).join("\n");
    $("paper-submit-btn").textContent = "Update Paper";
  } catch (e) {
    showMsg("paper-msg", e.message, false);
  }
}

function resetPaperForm() {
  editingPaperId = null;
  $("paper-form").reset();
  $("f-refcount").value = 0;
  $("f-citedby").value  = 0;
  $("edit-paper-select").value = "";
  $("edit-paper-input").value = "";
  $("paper-submit-btn").textContent = "Add Paper";
  $("f-cite-bibtex").value = "";
  $("f-aliases").value = "";
}

// ---------------------------------------------------------------------------
// Fill mode: auto-fill from BibTeX
// ---------------------------------------------------------------------------
async function autofillFromBibtex() {
  const bibtex = $("f-cite-bibtex").value.trim();
  if (!bibtex) return showMsg("paper-msg", "Paste a BibTeX entry first.", false);

  try {
    const data = await api("POST", "/api/bibtex/parse", { bibtex });

    if (data.title)      $("f-title").value    = data.title;
    if (data.year)       $("f-year").value     = data.year;
    if (data.authors)    $("f-authors").value  = data.authors;
    if (data.paper_link) $("f-link").value     = data.paper_link;
    if (data.abstract)   $("f-abstract").value = data.abstract;

    showMsg("paper-msg", "Auto-filled from BibTeX. Review and submit.", true);
  } catch (e) {
    showMsg("paper-msg", "BibTeX parse error: " + e.message, false);
  }
}

// ---------------------------------------------------------------------------
// Fill mode: submit paper (create or update, with citations)
// ---------------------------------------------------------------------------
async function submitPaper(e) {
  e.preventDefault();

  const citations = {};
  const bib = $("f-cite-bibtex").value.trim();
  if (bib) citations.BibTeX = bib;

  const aliases = $("f-aliases").value.split("\n").map(s => s.trim()).filter(Boolean);

  const payload = {
    title:         $("f-title").value.trim(),
    year:          $("f-year").value ? parseInt($("f-year").value) : null,
    authors:       $("f-authors").value.trim(),
    labels:        $("f-labels").value.trim(),
    ref_count:     parseInt($("f-refcount").value) || 0,
    cited_by_count:parseInt($("f-citedby").value)  || 0,
    abstract:      $("f-abstract").value.trim(),
    paper_link:    $("f-link").value.trim(),
    citations,
    aliases,
  };

  try {
    let res;
    if (editingPaperId) {
      res = await api("PUT", `/api/papers/${editingPaperId}`, payload);
      showMsg("paper-msg", "Paper updated.", true);
    } else {
      res = await api("POST", "/api/papers", payload);
      showMsg("paper-msg", `Paper created (id=${res.id}).`, true);
    }
    renderRematchResults(res.rematched || []);
    resetPaperForm();
    refreshPaperDropdowns();
  } catch (e) {
    showMsg("paper-msg", e.message, false);
    hideRematchResults();
  }
}

// ---------------------------------------------------------------------------
// Fill mode: re-match results display
// ---------------------------------------------------------------------------
function renderRematchResults(rematched) {
  const panel = $("rematch-results");
  if (!rematched.length) {
    panel.style.display = "none";
    return;
  }
  panel.style.display = "";
  $("rematch-summary").textContent = `${rematched.length} previously unresolved reference${rematched.length > 1 ? "s" : ""} now matched:`;
  const ul = $("rematch-list");
  ul.innerHTML = "";
  rematched.forEach(r => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="rematch-source">${esc(r.source_paper_title)}</span> → <span class="rematch-matched">${esc(r.matched_paper_title)}</span>`;
    ul.appendChild(li);
  });
}

function hideRematchResults() {
  $("rematch-results").style.display = "none";
}

// ---------------------------------------------------------------------------
// Fill mode: parse references
// ---------------------------------------------------------------------------
async function parseReferences() {
  const sourceId = $("ref-paper-select").value;
  const text     = $("ref-text").value.trim();
  if (!sourceId) return showMsg("refs-msg", "Select a source paper first.", false);
  if (!text)     return showMsg("refs-msg", "Paste reference text first.", false);

  try {
    const data = await api("POST", "/api/references/parse", {
      source_paper_id: parseInt(sourceId),
      text,
    });
    renderParsedRefs(data.references);
  } catch (e) {
    showMsg("refs-msg", e.message, false);
  }
}

function renderParsedRefs(refs) {
  $("parsed-refs").style.display = "";
  const matched = refs.filter(r => r.matched).length;
  $("parsed-count").textContent = `(${refs.length} total, ${matched} matched)`;
  const ul = $("ref-list");
  ul.innerHTML = "";

  refs.forEach((r, i) => {
    const li = document.createElement("li");

    let statusClass, tagClass, tagText;
    if (r.already_referenced) {
      statusClass = "status-already"; tagClass = "already"; tagText = "Already ref'd";
    } else if (r.matched) {
      statusClass = "status-in-db"; tagClass = "in-db"; tagText = "Matched";
    } else {
      statusClass = "status-not-in-db"; tagClass = "not-in-db"; tagText = "No match";
    }
    li.className = statusClass;

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = !r.already_referenced;
    cb.dataset.idx = i;

    const wrapper = document.createElement("div");
    wrapper.className = "ref-content";

    const fullText = document.createElement("div");
    fullText.className = "ref-full-text";
    fullText.textContent = r.raw_citation_text;

    const titleRow = document.createElement("div");
    titleRow.className = "ref-title-row";

    const titleLabel = document.createElement("span");
    titleLabel.className = "ref-title-label";
    titleLabel.textContent = r.matched ? "Matched:" : "Title:";

    const inp = document.createElement("input");
    inp.type = "text";
    inp.value = r.referenced_paper_title;
    inp.dataset.idx = i;
    inp.readOnly = r.matched;
    if (r.matched) inp.classList.add("matched-title");

    // Store hidden data for batch insert
    inp.dataset.rawCitation = r.raw_citation_text;
    inp.dataset.refId = r.referenced_paper_id ?? "";

    const tag = document.createElement("span");
    tag.className = `ref-tag ${tagClass}`;
    tag.textContent = tagText;

    titleRow.append(titleLabel, inp, tag);
    wrapper.append(fullText, titleRow);
    li.append(cb, wrapper);
    ul.appendChild(li);
  });
}

function toggleAllRefs(state) {
  document.querySelectorAll("#ref-list input[type=checkbox]").forEach(cb => { cb.checked = state; });
}

// ---------------------------------------------------------------------------
// Fill mode: batch insert references
// ---------------------------------------------------------------------------
async function batchInsertRefs() {
  const sourceId = $("ref-paper-select").value;
  const items = document.querySelectorAll("#ref-list li");
  const references = [];
  items.forEach(li => {
    const cb  = li.querySelector("input[type=checkbox]");
    const inp = li.querySelector(".ref-title-row input[type=text]");
    if (cb.checked && inp.dataset.rawCitation) {
      references.push({
        raw_citation_text: inp.dataset.rawCitation,
        referenced_paper_title: inp.value.trim(),
        referenced_paper_id: inp.dataset.refId ? parseInt(inp.dataset.refId) : null,
      });
    }
  });
  if (!references.length) return showMsg("refs-msg", "No references selected.", false);

  try {
    const res = await api("POST", "/api/references/batch", {
      source_paper_id: parseInt(sourceId),
      references,
    });
    let msg = `Inserted ${res.inserted}, skipped ${res.skipped_duplicates} duplicates.`;
    const rematched = res.rematched || [];
    if (rematched.length) msg += ` Auto-matched ${rematched.length} reference(s).`;
    showMsg("refs-msg", msg, true);
    renderRematchResults(rematched);
    $("parsed-refs").style.display = "none";
    $("ref-text").value = "";
  } catch (e) {
    showMsg("refs-msg", e.message, false);
  }
}

// ---------------------------------------------------------------------------
// Keyboard shortcut: Ctrl+Enter to execute
// ---------------------------------------------------------------------------
document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && currentMode === "search") {
    e.preventDefault();
    executeQuery();
  }
});

// ---------------------------------------------------------------------------
// Re-match references (manual trigger)
// ---------------------------------------------------------------------------
async function triggerRematch() {
  try {
    const res = await api("POST", "/api/references/rematch");
    if (res.count > 0) {
      renderRematchResults(res.rematched);
      alert(`Re-matched ${res.count} reference(s). See Fill tab for details.`);
    } else {
      alert("No new matches found.");
    }
  } catch (e) {
    alert("Re-match error: " + e.message);
  }
}

// ---------------------------------------------------------------------------
// Graph mode
// ---------------------------------------------------------------------------
let cy = null;
let graphSearchTimer = null;

function yearToColor(year, minY, maxY) {
  if (!year) return "#94a3b8";
  const span = Math.max(maxY - minY, 1);
  const t = (year - minY) / span;
  const r = Math.round(59 + t * (239 - 59));
  const g = Math.round(130 + (1 - Math.abs(t - 0.5) * 2) * (70));
  const b = Math.round(246 - t * (246 - 68));
  return `rgb(${r},${g},${b})`;
}

async function loadGraph() {
  const label = $("graph-label").value.trim();
  const yearMin = $("graph-year-min").value ? parseInt($("graph-year-min").value) : 0;
  const yearMax = $("graph-year-max").value ? parseInt($("graph-year-max").value) : 9999;

  let params = new URLSearchParams();
  if (label) params.set("label", label);
  if (yearMin) params.set("year_min", yearMin);
  if (yearMax < 9999) params.set("year_max", yearMax);

  const data = await api("GET", `/api/graph?${params}`);
  $("graph-info").textContent = `${data.nodes.length} papers, ${data.edges.length} citation edges`;

  if (!data.nodes.length) {
    if (cy) cy.destroy();
    cy = null;
    $("graph-info").textContent = "No connected papers found with current filters.";
    return;
  }

  const years = data.nodes.map(n => n.year).filter(Boolean);
  const minY = years.length ? Math.min(...years) : 2020;
  const maxY = years.length ? Math.max(...years) : 2026;
  const maxDeg = Math.max(1, ...data.nodes.map(n => n.in_degree));

  const elements = [];
  data.nodes.forEach(n => {
    const shortTitle = n.title.length > 45 ? n.title.slice(0, 42) + "..." : n.title;
    elements.push({
      group: "nodes",
      data: {
        id: String(n.id),
        label: `${shortTitle}\n(${n.year || "?"})`,
        fullTitle: n.title,
        year: n.year,
        authors: n.authors || "",
        labels: n.labels || "",
        paperLink: n.paper_link || "",
        inDegree: n.in_degree,
        nodeSize: 25 + (n.in_degree / maxDeg) * 45,
        nodeColor: yearToColor(n.year, minY, maxY),
      },
    });
  });
  data.edges.forEach(e => {
    elements.push({
      group: "edges",
      data: { source: String(e.source), target: String(e.target) },
    });
  });

  if (cy) cy.destroy();

  cy = cytoscape({
    container: $("cy-container"),
    elements,
    userZoomingEnabled: true,
    userPanningEnabled: true,
    boxSelectionEnabled: false,
    wheelSensitivity: 0.3,
    style: [
      {
        selector: "node",
        style: {
          "width": "data(nodeSize)",
          "height": "data(nodeSize)",
          "background-color": "data(nodeColor)",
          "label": "data(label)",
          "font-size": "9px",
          "text-wrap": "wrap",
          "text-max-width": "120px",
          "text-valign": "bottom",
          "text-margin-y": 6,
          "color": "#334155",
          "border-width": 1.5,
          "border-color": "#94a3b8",
        },
      },
      {
        selector: "node.highlighted",
        style: {
          "border-width": 4,
          "border-color": "#ef4444",
          "background-color": "#fca5a5",
          "z-index": 999,
        },
      },
      {
        selector: "edge",
        style: {
          "width": 1.5,
          "line-color": "#cbd5e1",
          "target-arrow-color": "#94a3b8",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          "arrow-scale": 0.8,
        },
      },
    ],
  });

  runGraphLayout();

  cy.on("tap", "node", function (evt) {
    const d = evt.target.data();
    $("tooltip-title").textContent = d.fullTitle;
    let meta = "";
    if (d.year) meta += `Year: ${d.year}`;
    if (d.authors) meta += `\nAuthors: ${d.authors}`;
    if (d.labels) meta += `\nLabels: ${d.labels}`;
    meta += `\nCited by: ${d.inDegree} paper(s) in DB`;
    $("tooltip-meta").textContent = meta;
    const link = $("tooltip-link");
    if (d.paperLink) {
      link.href = d.paperLink;
      link.style.display = "";
    } else {
      link.style.display = "none";
    }
    $("node-tooltip").style.display = "";
  });

  cy.on("tap", function (evt) {
    if (evt.target === cy) {
      $("node-tooltip").style.display = "none";
    }
  });
}

function runGraphLayout() {
  if (!cy) return;
  cy.layout({ name: "dagre", rankDir: "TB", nodeSep: 60, rankSep: 80, animate: true, animationDuration: 400 }).run();
}

function fitGraph() { if (cy) cy.fit(null, 30); }

function copyTooltipTitle() {
  const title = $("tooltip-title").textContent;
  navigator.clipboard.writeText(title).then(() => {
    const btn = $("node-tooltip").querySelector("button");
    btn.textContent = "Copied!";
    setTimeout(() => { btn.textContent = "Copy title"; }, 1500);
  });
}

function initGraphSearch() {
  $("graph-search").addEventListener("input", () => {
    clearTimeout(graphSearchTimer);
    graphSearchTimer = setTimeout(() => {
      if (!cy) return;
      const q = $("graph-search").value.trim().toLowerCase();
      cy.nodes().removeClass("highlighted");
      if (!q) return;
      cy.nodes().forEach(n => {
        if (n.data("fullTitle").toLowerCase().includes(q)) {
          n.addClass("highlighted");
        }
      });
    }, 400);
  });
}

// ---------------------------------------------------------------------------
// SQL text persistence (localStorage with 5s debounce)
// ---------------------------------------------------------------------------
const SQL_STORAGE_KEY = "paperdb_sql_text";
let sqlSaveTimer = null;

function initSqlPersistence() {
  const el = $("sql-input");
  const saved = localStorage.getItem(SQL_STORAGE_KEY);
  if (saved) el.value = saved;

  el.addEventListener("input", () => {
    clearTimeout(sqlSaveTimer);
    sqlSaveTimer = setTimeout(() => {
      localStorage.setItem(SQL_STORAGE_KEY, el.value);
    }, 5000);
  });
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  loadTables();
  initSqlPersistence();
  initGraphSearch();
  initSearchableSelect("edit-paper-input", "edit-paper-select", "edit-paper-list", (id) => {
    loadPaperForEdit(id);
  });
  initSearchableSelect("ref-paper-input", "ref-paper-select", "ref-paper-list", null);
});
