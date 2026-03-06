"""
Conference paper crawler.

Strategy:
  1. Use dblp search API to get ALL papers from specific conference proceedings.
  2. Pre-filter by title keywords (avoids expensive S2 calls for unrelated papers).
  3. Enrich keyword-matching papers with abstracts via Semantic Scholar.

  For venues where dblp returns 500 errors (RecSys, KDD), fall back to
  Semantic Scholar /paper/search which provides abstracts directly.

dblp search API: https://dblp.org/faq/How+to+use+the+dblp+search+API.html
Semantic Scholar API: https://api.semanticscholar.org/graph/v1
"""

import time
import logging
import requests
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

DBLP_API  = "https://dblp.org/search/publ/api"
S2_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "title,abstract,year,venue,authors,externalIds,url,publicationDate,openAccessPdf"

S2_VENUE_ALIASES = {
    "RecSys": ["recsys", "recommender systems"],
    "KDD":    ["kdd", "knowledge discovery", "sigkdd"],
    "WWW":    ["www", "web conference", "world wide web"],
    "SIGIR":  ["sigir", "information retrieval"],
}

# Seconds to wait between S2 API calls (free tier: ~1 req/s)
S2_DELAY = 1.5


def fetch(config: dict, known_titles: set = None) -> List[Dict]:
    conf_cfg = config["sources"]["conferences"]
    venues   = conf_cfg["venues"]
    years    = conf_cfg["years"]
    keywords = config["keywords"]["primary"] + config["keywords"]["secondary"]

    all_papers: List[Dict] = []
    # Seed seen_titles from DB so we skip already-stored papers
    seen_titles: set = set(known_titles) if known_titles else set()

    for venue_cfg in venues:
        stream  = venue_cfg["dblp_stream"]
        display = venue_cfg["name"]
        logger.info(f"=== {display} ===")

        for year in years:
            papers = _fetch_venue_year(stream, display, year, keywords, seen_titles)
            all_papers.extend(papers)
            time.sleep(1.0)

    logger.info(f"Conferences: collected {len(all_papers)} papers total")
    return all_papers


# ---------------------------------------------------------------------------
# Per-venue-year dispatch
# ---------------------------------------------------------------------------

def _fetch_venue_year(
    stream: str, display: str, year: int, keywords: List[str], seen_titles: set
) -> List[Dict]:
    papers = _dblp_fetch(stream, display, year, seen_titles)

    if papers:
        relevant = _title_filter(papers, keywords)
        logger.info(f"  {display} {year}: {len(papers)} dblp -> {len(relevant)} keyword-match")
        _enrich_abstracts(relevant)
        return relevant

    # dblp failed — use Semantic Scholar directly
    logger.info(f"  {display} {year}: dblp unavailable, using Semantic Scholar")
    papers = _s2_venue_fetch(display, year, keywords, seen_titles)
    logger.info(f"  {display} {year}: {len(papers)} papers via S2")
    return papers


# ---------------------------------------------------------------------------
# dblp
# ---------------------------------------------------------------------------

def _dblp_fetch(stream: str, display: str, year: int, seen_titles: set) -> List[Dict]:
    query  = f"streamid:{stream}: year:{year}"
    params = {"q": query, "format": "json", "h": 1000, "f": 0}

    try:
        resp = requests.get(DBLP_API, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"  dblp error for {display} {year}: {e}")
        return []

    hits = data.get("result", {}).get("hits", {}).get("hit", [])
    if not hits:
        return []

    papers = []
    for hit in hits:
        info  = hit.get("info", {})
        title = info.get("title", "").strip()
        if not title or title.lower() in seen_titles:
            continue

        hit_year = info.get("year")
        try:
            if hit_year and int(hit_year) != year:
                continue
        except ValueError:
            pass

        authors_raw = info.get("authors", {}).get("author", [])
        if isinstance(authors_raw, dict):
            authors_raw = [authors_raw]
        authors = [
            a.get("text", "") if isinstance(a, dict) else str(a)
            for a in authors_raw
        ]

        url = info.get("url", "") or info.get("ee", "")
        if isinstance(url, list):
            url = url[0] if url else ""

        doi = ""
        ee  = info.get("ee", "")
        if isinstance(ee, str) and "doi.org" in ee:
            doi = ee.split("doi.org/")[-1]

        paper = {
            "title":    title,
            "abstract": "",
            "authors":  authors,
            "date":     f"{year}-01-01",
            "year":     year,
            "url":      url,
            "arxiv_id": "",
            "doi":      doi,
            "source":   "conference",
            "venue":    display,
        }
        seen_titles.add(title.lower())
        papers.append(paper)

    logger.info(f"  {display} {year}: {len(papers)} papers from dblp")
    return papers


def _title_filter(papers: List[Dict], keywords: List[str]) -> List[Dict]:
    kw_lower = [kw.lower() for kw in keywords]
    return [p for p in papers if any(kw in p["title"].lower() for kw in kw_lower)]


# ---------------------------------------------------------------------------
# Semantic Scholar fallback venue fetch
# ---------------------------------------------------------------------------

def _s2_venue_fetch(
    display: str, year: int, keywords: List[str], seen_titles: set
) -> List[Dict]:
    aliases  = S2_VENUE_ALIASES.get(display, [display.lower()])
    papers   = []
    seen_ids: set = set()

    for kw in keywords:
        items = _s2_search_with_retry(f"{kw} {display}", year=year)
        for item in items:
            pid        = item.get("paperId", "")
            if pid in seen_ids:
                continue
            item_venue = (item.get("venue") or "").lower()
            if not any(alias in item_venue for alias in aliases):
                continue
            if item.get("year") != year:
                continue

            title = (item.get("title") or "").strip()
            if not title or title.lower() in seen_titles:
                continue

            seen_ids.add(pid)
            seen_titles.add(title.lower())
            papers.append(_s2_item_to_paper(item, display, year))

        time.sleep(S2_DELAY)

    return papers


# ---------------------------------------------------------------------------
# Abstract enrichment (for dblp-sourced papers)
# ---------------------------------------------------------------------------

def _enrich_abstracts(papers: List[Dict]) -> None:
    no_abs = [p for p in papers if not p["abstract"]]
    if not no_abs:
        return
    logger.info(f"  Enriching {len(no_abs)} abstracts via S2...")

    for i, paper in enumerate(no_abs):
        items = _s2_search_with_retry(paper["title"], limit=3)
        for item in items:
            if (item.get("title") or "").strip().lower() == paper["title"].lower():
                paper["abstract"] = (item.get("abstract") or "").strip()
                if not paper["url"]:
                    paper["url"] = item.get("url") or ""
                ext = item.get("externalIds") or {}
                if not paper["arxiv_id"]:
                    paper["arxiv_id"] = ext.get("ArXiv", "")
                break

        if (i + 1) % 10 == 0:
            logger.info(f"    {i + 1}/{len(no_abs)}")
        time.sleep(S2_DELAY)


# ---------------------------------------------------------------------------
# S2 helpers
# ---------------------------------------------------------------------------

def _s2_search_with_retry(
    query: str,
    year: Optional[int] = None,
    limit: int = 100,
    max_retries: int = 4,
) -> List[Dict]:
    params: Dict = {"query": query, "fields": S2_FIELDS, "limit": limit}
    if year:
        params["year"] = str(year)

    wait = 5.0
    for attempt in range(max_retries):
        try:
            resp = requests.get(S2_SEARCH, params=params, timeout=20)
            if resp.status_code == 429:
                logger.info(f"  S2 rate-limited, waiting {wait:.0f}s...")
                time.sleep(wait)
                wait *= 2
                continue
            resp.raise_for_status()
            return resp.json().get("data", [])
        except requests.HTTPError:
            logger.warning(f"  S2 HTTP error for query '{query[:60]}'")
            break
        except Exception as e:
            logger.warning(f"  S2 error: {e}")
            time.sleep(wait)
            wait *= 2

    return []


def _s2_item_to_paper(item: Dict, venue: str, year: int) -> Dict:
    authors  = [a.get("name", "") for a in (item.get("authors") or [])]
    abstract = (item.get("abstract") or "").strip()
    url      = item.get("url") or ""
    ext_ids  = item.get("externalIds") or {}
    arxiv_id = ext_ids.get("ArXiv", "")
    doi      = ext_ids.get("DOI", "")
    pub_date = item.get("publicationDate") or f"{year}-01-01"
    if not url:
        pdf = item.get("openAccessPdf") or {}
        url = pdf.get("url", "")

    return {
        "title":    (item.get("title") or "").strip(),
        "abstract": abstract,
        "authors":  authors,
        "date":     pub_date,
        "year":     year,
        "url":      url,
        "arxiv_id": arxiv_id,
        "doi":      doi,
        "source":   "conference",
        "venue":    venue,
    }
