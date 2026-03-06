"""
Export papers to a self-contained HTML file.
Single "Papers" tab with search / filter / sort.
Papers with an AI summary show an "AI Summary" button next to the score tag;
clicking it toggles a 3-sentence summary panel inline.
"""

import html
import json
from datetime import datetime
from typing import List, Dict

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>CTR/CVR RecSys Papers</title>
<style>
  :root {
    --bg: #0f1117; --surface: #1a1d27; --surface2: #252836;
    --border: #2e3347; --accent: #6c63ff; --accent2: #00d4aa;
    --text: #e2e8f0; --muted: #8892a4;
    --tag-arxiv: #1e3a5f; --tag-conf: #1e4a2e;
    --tag-arxiv-text: #60a5fa; --tag-conf-text: #4ade80;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: var(--bg); color: var(--text); min-height: 100vh; }

  /* Header */
  header { background: var(--surface); border-bottom: 1px solid var(--border);
           padding: 18px 32px; position: sticky; top: 0; z-index: 100; }
  header h1 { font-size: 1.35rem; font-weight: 700; color: var(--accent);
              display: inline-flex; align-items: center; gap: 10px; }
  header .subtitle { color: var(--muted); font-size: 0.82rem; margin-top: 3px; }

  /* Controls */
  .controls { display: flex; flex-wrap: wrap; gap: 12px; padding: 16px 32px;
              background: var(--surface); border-bottom: 1px solid var(--border); }
  .search-wrap { flex: 1; min-width: 220px; position: relative; }
  .search-wrap svg { position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
                     width: 16px; height: 16px; }
  input[type="search"] {
    width: 100%; padding: 9px 12px 9px 36px;
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 8px; color: var(--text); font-size: 0.9rem; outline: none;
    transition: border-color .2s;
  }
  input[type="search"]:focus { border-color: var(--accent); }
  input[type="search"]::placeholder { color: var(--muted); }
  select {
    padding: 9px 14px; background: var(--surface2); border: 1px solid var(--border);
    border-radius: 8px; color: var(--text); font-size: 0.9rem; cursor: pointer; outline: none;
  }
  select:focus { border-color: var(--accent); }
  .count-badge { align-self: center; color: var(--muted); font-size: 0.82rem;
                 margin-left: auto; white-space: nowrap; }

  /* Container */
  .container { max-width: 1100px; margin: 0 auto; padding: 22px 32px; }

  /* Paper Card */
  .paper-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 18px 22px; margin-bottom: 14px;
    transition: border-color .2s, transform .1s;
    animation: fadeIn .25s ease;
  }
  .paper-card:hover { border-color: var(--accent); transform: translateY(-1px); }
  @keyframes fadeIn { from { opacity:0; transform: translateY(5px); } to { opacity:1; transform:none; } }

  .card-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
  .card-title { font-size: 1rem; font-weight: 600; line-height: 1.5; flex: 1; }
  .card-title a { color: var(--text); text-decoration: none; }
  .card-title a:hover { color: var(--accent); }

  .tags { display: flex; gap: 6px; flex-wrap: wrap; flex-shrink: 0; margin-top: 2px; align-items: center; }
  .tag { font-size: 0.7rem; font-weight: 600; padding: 3px 8px;
         border-radius: 20px; letter-spacing: .02em; white-space: nowrap; }
  .tag-arxiv { background: var(--tag-arxiv); color: var(--tag-arxiv-text); }
  .tag-conf  { background: var(--tag-conf);  color: var(--tag-conf-text);  }
  .tag-venue { background: var(--surface2); color: var(--muted); border: 1px solid var(--border); }
  .tag-year  { background: var(--surface2); color: var(--muted); border: 1px solid var(--border); }
  .tag-score { background: #2d1f4a; color: #a78bfa; border: 1px solid #4c3888; }

  /* AI Summary button */
  .btn-summary {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 10px; border-radius: 20px; border: 1px solid var(--accent2);
    background: transparent; color: var(--accent2); font-size: 0.7rem; font-weight: 600;
    cursor: pointer; letter-spacing: .02em; white-space: nowrap;
    transition: background .15s, color .15s;
  }
  .btn-summary:hover { background: var(--accent2); color: #0f1117; }
  .btn-summary svg { width: 11px; height: 11px; flex-shrink: 0; }

  /* Inline summary panel */
  .summary-panel {
    display: none; margin-top: 12px;
    background: var(--surface2); border: 1px solid var(--accent2);
    border-radius: 8px; padding: 14px 16px;
    font-size: 0.87rem; line-height: 1.75; color: #cbd5e1;
    position: relative;
  }
  .summary-panel.open { display: block; animation: fadeIn .2s ease; }
  .summary-panel::before {
    content: '✦ AI Summary';
    display: block; font-size: 0.7rem; font-weight: 700; color: var(--accent2);
    text-transform: uppercase; letter-spacing: .08em; margin-bottom: 8px;
  }
  .summary-sentence { display: block; padding: 2px 0; }
  .summary-sentence + .summary-sentence { margin-top: 4px; }
  .s-num { color: var(--accent2); font-weight: 700; margin-right: 4px; }

  .card-authors { margin-top: 7px; color: var(--muted); font-size: 0.82rem; }
  .card-abstract {
    margin-top: 10px; color: #94a3b8; font-size: 0.87rem; line-height: 1.65;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
    cursor: pointer;
  }
  .card-abstract.expanded { -webkit-line-clamp: unset; }
  .expand-btn { margin-top: 5px; font-size: 0.78rem; color: var(--accent);
                cursor: pointer; background: none; border: none; padding: 0; }
  .expand-btn:hover { text-decoration: underline; }

  /* Empty state */
  .empty { text-align: center; padding: 70px 20px; color: var(--muted); }

  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: var(--bg); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
</head>
<body>

<header>
  <h1>
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6c63ff" stroke-width="2">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
    </svg>
    CTR/CVR &amp; RecSys Papers
  </h1>
  <div class="subtitle">arXiv + RecSys / KDD / WWW / SIGIR &nbsp;|&nbsp; 2023–present &nbsp;|&nbsp; __GENERATED__</div>
</header>

<div class="controls">
  <div class="search-wrap">
    <svg viewBox="0 0 24 24" fill="none" stroke="#8892a4" stroke-width="2" stroke-linecap="round">
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
    </svg>
    <input type="search" id="searchBox" placeholder="Search title, abstract, authors..."
           oninput="applyFilters()"/>
  </div>
  <select id="venueFilter" onchange="applyFilters()">
    <option value="">All Venues</option>
    __VENUE_OPTIONS__
  </select>
  <select id="yearFilter" onchange="applyFilters()">
    <option value="">All Years</option>
    __YEAR_OPTIONS__
  </select>
  <select id="sortBy" onchange="applyFilters()">
    <option value="score">Sort: Relevance</option>
    <option value="date_desc">Sort: Newest</option>
    <option value="date_asc">Sort: Oldest</option>
  </select>
  <span class="count-badge" id="countBadge"></span>
</div>

<div class="container">
  <div id="paperList"></div>
  <div class="empty" id="emptyState" style="display:none">No papers match your filters.</div>
</div>

<script>
const PAPERS = __PAPERS_JSON__;
let filtered = [...PAPERS];

function applyFilters() {
  const q     = document.getElementById('searchBox').value.toLowerCase();
  const venue = document.getElementById('venueFilter').value;
  const year  = document.getElementById('yearFilter').value;
  const sort  = document.getElementById('sortBy').value;

  filtered = PAPERS.filter(p => {
    if (venue && p.venue !== venue) return false;
    if (year  && String(p.year) !== year) return false;
    if (q) {
      const hay = (p.title + ' ' + p.abstract + ' ' + (p.authors||[]).join(' ')).toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  if (sort === 'score')        filtered.sort((a,b) => (b.score-a.score)||(b.date||'').localeCompare(a.date||''));
  else if (sort==='date_desc') filtered.sort((a,b) => (b.date||'').localeCompare(a.date||''));
  else                         filtered.sort((a,b) => (a.date||'').localeCompare(b.date||''));

  renderList();
}

function renderList() {
  const list  = document.getElementById('paperList');
  const empty = document.getElementById('emptyState');
  document.getElementById('countBadge').textContent = filtered.length + ' / ' + PAPERS.length + ' papers';

  if (!filtered.length) { list.innerHTML=''; empty.style.display='block'; return; }
  empty.style.display = 'none';

  list.innerHTML = filtered.map((p, idx) => {
    const srcTag = p.source === 'arxiv'
      ? '<span class="tag tag-arxiv">arXiv</span>'
      : '<span class="tag tag-conf">Conference</span>';
    const vTag   = p.source !== 'arxiv' ? `<span class="tag tag-venue">${esc(p.venue)}</span>` : '';
    const yTag   = p.year ? `<span class="tag tag-year">${p.year}</span>` : '';
    const sTag   = `<span class="tag tag-score">score ${p.score}</span>`;

    const aiBtn  = p.summary
      ? `<button class="btn-summary" onclick="toggleSummary(${idx})">
           <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
             <path d="M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2z"/>
             <path d="M12 8v4l3 3"/>
           </svg>
           AI Summary
         </button>`
      : '';

    const titleHtml = p.url
      ? `<a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.title)}</a>`
      : esc(p.title);

    const authors = p.authors || [];
    const authStr = authors.slice(0,5).join(', ') + (authors.length > 5 ? ` +${authors.length-5}` : '');

    const abst = p.abstract
      ? `<div class="card-abstract" id="abs-${idx}">${esc(p.abstract)}</div>
         <button class="expand-btn" onclick="toggleAbs(${idx})">Show more</button>`
      : '<div style="color:var(--muted);font-size:.8rem;margin-top:8px;font-style:italic">No abstract available</div>';

    let summaryPanel = '';
    if (p.summary) {
      const sentences = p.summary.replace(/\\n/g,' ').split(/(?<=\\.)\s+/).filter(s => s.trim());
      const sentHtml = sentences.map((s, i) =>
        `<span class="summary-sentence"><span class="s-num">${i+1}.</span>${esc(s.replace(/\\.$/,''))}</span>`
      ).join('');
      summaryPanel = `<div class="summary-panel" id="sum-${idx}">${sentHtml}</div>`;
    }

    return `<div class="paper-card">
  <div class="card-header">
    <div class="card-title">${titleHtml}</div>
    <div class="tags">${srcTag}${vTag}${yTag}${sTag}${aiBtn}</div>
  </div>
  <div class="card-authors">${esc(authStr)}</div>
  ${abst}
  ${summaryPanel}
</div>`;
  }).join('');
}

function toggleSummary(idx) {
  const panel = document.getElementById('sum-' + idx);
  if (!panel) return;
  panel.classList.toggle('open');
}

function toggleAbs(idx) {
  const el  = document.getElementById('abs-' + idx);
  const btn = el.nextElementSibling;
  el.classList.toggle('expanded')
    ? btn.textContent = 'Show less'
    : btn.textContent = 'Show more';
}

function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

applyFilters();
</script>
</body>
</html>"""


def export(papers: List[Dict], output_path: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    venues = sorted(set(p.get("venue", "") for p in papers if p.get("venue")))
    venue_options = "\n".join(
        f'    <option value="{html.escape(v)}">{html.escape(v)}</option>' for v in venues
    )

    years = sorted(set(p.get("year") for p in papers if p.get("year")), reverse=True)
    year_options = "\n".join(
        f'    <option value="{y}">{y}</option>' for y in years
    )

    papers_json = json.dumps(
        [
            {
                "title":    p.get("title", ""),
                "abstract": p.get("abstract", ""),
                "authors":  p.get("authors", []),
                "date":     p.get("date", ""),
                "year":     p.get("year"),
                "venue":    p.get("venue", ""),
                "source":   p.get("source", ""),
                "url":      p.get("url", ""),
                "score":    p.get("score", 0),
                "summary":  p.get("summary") or "",
            }
            for p in papers
        ],
        ensure_ascii=False,
    )

    rendered = (
        HTML_TEMPLATE
        .replace("__GENERATED__", html.escape(now))
        .replace("__VENUE_OPTIONS__", venue_options)
        .replace("__YEAR_OPTIONS__", year_options)
        .replace("__PAPERS_JSON__", papers_json)
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    # Also write index.html at repo root for GitHub Pages
    import os
    root_index = os.path.join(os.path.dirname(os.path.dirname(output_path)), "index.html")
    with open(root_index, "w", encoding="utf-8") as f:
        f.write(rendered)

    summarized = sum(1 for p in papers if p.get("summary"))
    print(f"HTML saved: {output_path} ({len(papers)} papers, {summarized} with summaries)")
