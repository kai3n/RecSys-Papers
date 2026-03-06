# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Crawls research papers on **CTR/CVR prediction and recommender systems** from arXiv and top conferences (RecSys, KDD, WWW, SIGIR), scores them by keyword relevance, stores them in SQLite, and exports to HTML and Markdown.

## Commands

```bash
# Install dependencies
pip3 install -r requirements.txt

# Full crawl (arXiv + conferences) — takes ~5–10 min
python3 main.py

# Partial crawls
python3 main.py --arxiv-only
python3 main.py --conf-only

# Re-export from existing DB without re-crawling
python3 main.py --export-only

# Stricter keyword filter (default is 1)
python3 main.py --min-score 3
```

Outputs go to `output/papers.html`, `output/papers.md`, and `output/papers.db`.

## Architecture

```
main.py                      # Orchestrates: crawl → filter → save → export
config.yaml                  # All tunable settings (keywords, venues, date range)

crawlers/
  arxiv_crawler.py           # arXiv Atom API (export.arxiv.org/api/query)
  conference_crawler.py      # dblp → S2 enrichment; S2-only fallback on dblp 500s

parsers/
  keyword_filter.py          # Scores papers: title match (+5/+2), abstract match (+3/+1)
                             # Deduplicates by normalized title

storage/
  db.py                      # SQLite with UNIQUE index on title — safe to re-run

exporters/
  to_html.py                 # Self-contained SPA (dark theme, search/filter/sort, no deps)
  to_markdown.py             # Grouped by venue → year
```

## Data flow

1. **arXiv**: keyword + category query → Atom feed → list of papers (no abstracts from S2)
2. **Conferences**: dblp `streamid:conf/<venue>: year:<Y>` → all papers → title pre-filter → S2 abstract enrichment. If dblp returns 500, falls back to S2 keyword+venue search (abstracts included directly).
3. **Filter**: `keyword_filter.py` scores and deduplicates combined results
4. **DB**: SQLite deduplicates on title — incremental runs skip already-seen papers
5. **Export**: both exporters read from DB, not from in-memory results

## Known issues / gotchas

- **dblp 500 errors**: The `streamid:` filter intermittently fails for some venues (observed for RecSys 2023/2024, KDD, WWW). The fallback is Semantic Scholar keyword search.
- **S2 rate limiting (429)**: S2 free tier is ~1 req/s. The crawler uses 1.5s delay + exponential backoff (5s→10s→20s→40s). If you hit sustained 429s, wait a few minutes before re-running.
- **dblp + S2 for abstracts**: dblp gives titles/authors only; S2 is queried per-paper for abstracts. Only keyword-matching papers are enriched (pre-filter saves many S2 calls).

## Extending

- **Add a venue**: add entry under `sources.conferences.venues` in `config.yaml` with `name` and `dblp_stream` (find the stream at `dblp.org/db/conf/<name>/`).
- **Add keywords**: edit `keywords.primary` or `keywords.secondary` in `config.yaml`. Primary keywords score higher.
- **Change output format**: implement a new exporter in `exporters/` following the same `export(papers, output_path)` signature, then call it from `main.py`.
