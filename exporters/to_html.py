"""
Export papers to a self-contained HTML file with search, filter, and sort UI.
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
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #252836;
    --border: #2e3347;
    --accent: #6c63ff;
    --accent2: #00d4aa;
    --text: #e2e8f0;
    --muted: #8892a4;
    --tag-arxiv: #1e3a5f;
    --tag-conf: #1e4a2e;
    --tag-arxiv-text: #60a5fa;
    --tag-conf-text: #4ade80;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: var(--bg); color: var(--text); min-height: 100vh; }

  /* Header */
  header { background: var(--surface); border-bottom: 1px solid var(--border);
           padding: 20px 32px; position: sticky; top: 0; z-index: 100;
           backdrop-filter: blur(10px); }
  header h1 { font-size: 1.4rem; font-weight: 700; color: var(--accent);
              display: inline-flex; align-items: center; gap: 10px; }
  header .subtitle { color: var(--muted); font-size: 0.85rem; margin-top: 4px; }

  /* Controls */
  .controls { display: flex; flex-wrap: wrap; gap: 12px; padding: 20px 32px;
              background: var(--surface); border-bottom: 1px solid var(--border);
              position: sticky; top: 73px; z-index: 99; }
  .search-wrap { flex: 1; min-width: 220px; position: relative; }
  .search-wrap svg { position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
                     width: 16px; height: 16px; fill: var(--muted); }
  input[type="search"] {
    width: 100%; padding: 10px 12px 10px 38px;
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 8px; color: var(--text); font-size: 0.9rem;
    outline: none; transition: border-color .2s;
  }
  input[type="search"]:focus { border-color: var(--accent); }
  input[type="search"]::placeholder { color: var(--muted); }

  select {
    padding: 10px 14px; background: var(--surface2); border: 1px solid var(--border);
    border-radius: 8px; color: var(--text); font-size: 0.9rem; cursor: pointer;
    outline: none; min-width: 130px;
  }
  select:focus { border-color: var(--accent); }
  .count-badge { align-self: center; color: var(--muted); font-size: 0.85rem;
                 margin-left: auto; white-space: nowrap; }

  /* Layout */
  .container { max-width: 1100px; margin: 0 auto; padding: 24px 32px; }

  /* Paper Card */
  .paper-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px 24px; margin-bottom: 16px;
    transition: border-color .2s, transform .1s;
    animation: fadeIn .3s ease;
  }
  .paper-card:hover { border-color: var(--accent); transform: translateY(-1px); }
  @keyframes fadeIn { from { opacity:0; transform: translateY(6px); } to { opacity:1; transform:none; } }

  .card-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
  .card-title { font-size: 1.05rem; font-weight: 600; line-height: 1.5; flex: 1; }
  .card-title a { color: var(--text); text-decoration: none; }
  .card-title a:hover { color: var(--accent); }

  .tags { display: flex; gap: 6px; flex-wrap: wrap; flex-shrink: 0; margin-top: 2px; }
  .tag {
    font-size: 0.72rem; font-weight: 600; padding: 3px 9px;
    border-radius: 20px; letter-spacing: 0.02em; white-space: nowrap;
  }
  .tag-arxiv { background: var(--tag-arxiv); color: var(--tag-arxiv-text); }
  .tag-conf  { background: var(--tag-conf);  color: var(--tag-conf-text);  }
  .tag-venue { background: var(--surface2); color: var(--muted); border: 1px solid var(--border); }
  .tag-year  { background: var(--surface2); color: var(--muted); border: 1px solid var(--border); }
  .tag-score { background: #2d1f4a; color: #a78bfa; border: 1px solid #4c3888; }

  .card-authors { margin-top: 8px; color: var(--muted); font-size: 0.85rem; }
  .card-abstract {
    margin-top: 12px; color: #94a3b8; font-size: 0.88rem; line-height: 1.65;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
    overflow: hidden; cursor: pointer;
  }
  .card-abstract.expanded { -webkit-line-clamp: unset; }
  .expand-btn {
    margin-top: 6px; font-size: 0.8rem; color: var(--accent);
    cursor: pointer; background: none; border: none; padding: 0;
  }
  .expand-btn:hover { text-decoration: underline; }

  /* Empty state */
  .empty { text-align: center; padding: 80px 20px; color: var(--muted); }
  .empty svg { width: 48px; height: 48px; margin-bottom: 16px; fill: var(--border); }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: var(--bg); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
</head>
<body>

<header>
  <h1>
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6c63ff" stroke-width="2">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
    </svg>
    CTR/CVR &amp; RecSys Papers
  </h1>
  <div class="subtitle">arXiv + RecSys / KDD / WWW / SIGIR &nbsp;|&nbsp; 2023–present &nbsp;|&nbsp; Generated: __GENERATED__</div>
</header>

<div class="controls">
  <div class="search-wrap">
    <svg viewBox="0 0 24 24"><path d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" stroke="#8892a4" stroke-width="2" fill="none" stroke-linecap="round"/></svg>
    <input type="search" id="searchBox" placeholder="Search title, abstract, authors..." oninput="applyFilters()"/>
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
  <div class="empty" id="emptyState" style="display:none">
    <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
    <div>No papers found matching your filters.</div>
  </div>
</div>

<script>
const PAPERS = __PAPERS_JSON__;

let filtered = [...PAPERS];

function applyFilters() {
  const q = document.getElementById('searchBox').value.toLowerCase();
  const venue = document.getElementById('venueFilter').value;
  const year = document.getElementById('yearFilter').value;
  const sort = document.getElementById('sortBy').value;

  filtered = PAPERS.filter(p => {
    if (venue && p.venue !== venue) return false;
    if (year && String(p.year) !== year) return false;
    if (q) {
      const hay = (p.title + ' ' + p.abstract + ' ' + (p.authors||[]).join(' ')).toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  if (sort === 'score') {
    filtered.sort((a, b) => (b.score - a.score) || (b.date || '').localeCompare(a.date || ''));
  } else if (sort === 'date_desc') {
    filtered.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
  } else {
    filtered.sort((a, b) => (a.date || '').localeCompare(b.date || ''));
  }

  renderList();
}

function renderList() {
  const list = document.getElementById('paperList');
  const empty = document.getElementById('emptyState');
  const badge = document.getElementById('countBadge');

  badge.textContent = filtered.length + ' / ' + PAPERS.length + ' papers';

  if (filtered.length === 0) {
    list.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  list.innerHTML = filtered.map((p, idx) => {
    const sourceTag = p.source === 'arxiv'
      ? '<span class="tag tag-arxiv">arXiv</span>'
      : '<span class="tag tag-conf">Conference</span>';
    const venueTag = `<span class="tag tag-venue">${esc(p.venue)}</span>`;
    const yearTag = p.year ? `<span class="tag tag-year">${p.year}</span>` : '';
    const scoreTag = `<span class="tag tag-score">score ${p.score}</span>`;

    const titleHtml = p.url
      ? `<a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.title)}</a>`
      : esc(p.title);

    const authors = (p.authors || []);
    const authorStr = authors.slice(0, 5).join(', ') + (authors.length > 5 ? ` +${authors.length - 5} more` : '');

    const abstract = p.abstract
      ? `<div class="card-abstract" id="abs-${idx}">${esc(p.abstract)}</div>
         <button class="expand-btn" onclick="toggleAbs(${idx})">Show more</button>`
      : '<div style="color:var(--muted);font-size:.82rem;margin-top:8px;font-style:italic">No abstract available</div>';

    return `<div class="paper-card">
  <div class="card-header">
    <div class="card-title">${titleHtml}</div>
    <div class="tags">${sourceTag}${venueTag}${yearTag}${scoreTag}</div>
  </div>
  <div class="card-authors">${esc(authorStr)}</div>
  ${abstract}
</div>`;
  }).join('');
}

function toggleAbs(idx) {
  const el = document.getElementById('abs-' + idx);
  const btn = el.nextElementSibling;
  if (el.classList.toggle('expanded')) {
    btn.textContent = 'Show less';
  } else {
    btn.textContent = 'Show more';
  }
}

function esc(s) {
  if (!s) return '';
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Initial render
applyFilters();
</script>
</body>
</html>"""


def export(papers: List[Dict], output_path: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Venue options
    venues = sorted(set(p.get("venue", "") for p in papers if p.get("venue")))
    venue_options = "\n".join(
        f'    <option value="{html.escape(v)}">{html.escape(v)}</option>' for v in venues
    )

    # Year options
    years = sorted(set(p.get("year") for p in papers if p.get("year")), reverse=True)
    year_options = "\n".join(
        f'    <option value="{y}">{y}</option>' for y in years
    )

    # Serialize papers for JS
    papers_json = json.dumps(
        [
            {
                "title": p.get("title", ""),
                "abstract": p.get("abstract", ""),
                "authors": p.get("authors", []),
                "date": p.get("date", ""),
                "year": p.get("year"),
                "venue": p.get("venue", ""),
                "source": p.get("source", ""),
                "url": p.get("url", ""),
                "score": p.get("score", 0),
            }
            for p in papers
        ],
        ensure_ascii=False,
        indent=None,
    )

    rendered = (
        HTML_TEMPLATE.replace("__GENERATED__", html.escape(now))
        .replace("__VENUE_OPTIONS__", venue_options)
        .replace("__YEAR_OPTIONS__", year_options)
        .replace("__PAPERS_JSON__", papers_json)
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    print(f"HTML saved: {output_path} ({len(papers)} papers)")
